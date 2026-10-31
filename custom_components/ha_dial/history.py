"""Recorded metric history for the Data faces: fetched once, then kept current by state events."""

import logging
from datetime import timedelta
from functools import partial

from homeassistant.util import dt as dt_util

from .catalogue import DATA_STYLES
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
BINS = 48


def _binned(samples, start, end):
    """Average into fixed bins, carrying forward so that a quiet sensor still reads as a level."""
    span = (end - start).total_seconds() or 1
    totals = [[0.0, 0] for _ in range(BINS)]
    for when, value in samples:
        index = min(BINS - 1, max(0, int((when - start).total_seconds() * BINS / span)))
        totals[index][0] += value
        totals[index][1] += 1
    result, last = [], None
    for total, count in totals:
        last = total / count if count else last
        result.append(last)
    return [value for value in result if value is not None]


async def ensure_history(hass, view: dict) -> None:
    """Load a Data face's series on first sight; a missing recorder reads as no history."""
    if view.get("style") not in DATA_STYLES:
        return
    state = hass.data[DOMAIN]
    cache = state.setdefault("history", {})
    samples = state.setdefault("history_samples", {})
    hours = view.get("clock", {}).get("history_hours", 24)
    end = dt_util.utcnow()
    start = end - timedelta(hours=hours)
    for metric in view.get("clock", {}).get("metrics", []):
        entity = metric["entity_id"]
        if entity in cache:
            continue
        cache[entity] = []
        samples[entity] = []
        if "recorder" not in hass.config.components:
            _LOGGER.info("No recorder is loaded, so %s has no history to plot", entity)
            continue
        from homeassistant.components.recorder import get_instance, history

        try:
            states = await get_instance(hass).async_add_executor_job(
                partial(history.state_changes_during_period, hass, start, entity_id=entity, no_attributes=True)
            )
        except Exception as error:  # noqa: BLE001 - a chart failing must never take the Dial's page down.
            _LOGGER.warning("Could not read history for %s: %s", entity, error)
            continue
        for recorded in states.get(entity, []):
            try:
                samples[entity].append((recorded.last_changed, float(recorded.state)))
            except (TypeError, ValueError):
                continue
        cache[entity] = _binned(samples[entity], start, end)


def record_change(hass, entity: str, new_state, hours: int = 24) -> None:
    """Keep a loaded series current from the state event, rather than querying again."""
    state = hass.data[DOMAIN]
    samples = state.get("history_samples", {}).get(entity)
    if samples is None or new_state is None:
        return
    try:
        samples.append((new_state.last_changed, float(new_state.state)))
    except (TypeError, ValueError):
        return
    end = dt_util.utcnow()
    start = end - timedelta(hours=hours)
    samples[:] = [sample for sample in samples if sample[0] >= start]
    state["history"][entity] = _binned(samples, start, end)


def forget_history(hass) -> None:
    state = hass.data[DOMAIN]
    state.pop("history", None)
    state.pop("history_samples", None)
