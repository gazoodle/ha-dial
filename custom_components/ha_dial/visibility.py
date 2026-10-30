"""Event-driven HA visibility; configuration never becomes browser-dependent."""

import json
import math
import re
from copy import deepcopy


def condition_template(config: dict) -> str:
    """Compile the state-based HA condition subset into a tracked HA template."""
    if not isinstance(config, dict):
        raise TypeError("Each visibility condition must be an object")
    if "enabled" in config and not isinstance(config["enabled"], bool):
        raise TypeError("Condition enabled must be a boolean")
    kind = config.get("condition")
    options = config.get("options", config)
    if config.get("enabled") is False:
        return "{{ true }}"
    if kind == "template":
        source = options.get("value_template")
        if not isinstance(source, str):
            raise ValueError("Template conditions need value_template text")
        return source
    if kind == "time":
        bounds = {}
        for name in ("after", "before"):
            value = options.get(name)
            if value is None:
                continue
            if not isinstance(value, str) or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?", value):
                raise ValueError("Time conditions require a fixed time in HH:MM or HH:MM:SS format")
            bounds[name] = value if len(value) == 8 else value + ":00"
        days = options.get("weekday")
        if isinstance(days, str):
            days = [days]
        if days is not None and (not isinstance(days, list) or not days or any(day not in ("mon", "tue", "wed", "thu", "fri", "sat", "sun") for day in days)):
            raise ValueError("Time conditions need valid weekdays")
        if not bounds and not days:
            raise ValueError("Choose a time or weekday")
        parts = []
        if days:
            parts.append("now().weekday() in " + repr([("mon", "tue", "wed", "thu", "fri", "sat", "sun").index(day) for day in days]))
        after, before = bounds.get("after"), bounds.get("before")
        checks = []
        if after:
            checks.append("now().strftime('%H:%M:%S') >= " + json.dumps(after))
        if before:
            checks.append("now().strftime('%H:%M:%S') < " + json.dumps(before))
        if checks:
            parts.append("(" + (" or " if after and before and after > before else " and ").join(checks) + ")")
        return "{{ " + " and ".join(parts) + " }}"
    if kind not in {"state", "numeric_state"}:
        raise ValueError(
            "Visibility supports state, numeric_state, time, template and and/or/not conditions; device and browser conditions are not supported"
        )
    if kind == "numeric_state" and "value_template" in options:
        raise ValueError(
            "Use a template condition for numeric value_template expressions"
        )
    if "for" in options:
        raise ValueError(
            "Visibility state conditions do not support a for duration; use an HA template sensor"
        )
    entities = options.get("entity_id")
    if isinstance(entities, str):
        entities = [entities]
    if (
        not isinstance(entities, list)
        or not entities
        or not all(isinstance(e, str) and "." in e for e in entities)
    ):
        raise ValueError("Visibility conditions need entity_id")
    expressions = []
    for entity in entities:
        entity = json.dumps(entity)
        attr = options.get("attribute")
        if attr is not None and not isinstance(attr, str):
            raise TypeError("Condition attribute must be text")
        value = (
            f"state_attr({entity}, {json.dumps(attr)})" if attr else f"states({entity})"
        )
        if kind == "state":
            states = options.get("state")
            states = states if isinstance(states, list) else [states]
            if not all(isinstance(s, str) for s in states):
                raise ValueError("State conditions need a state")
            expressions.append(f"({value} in {json.dumps(states)})")
        else:
            checks = [f"({value} | is_number)"]
            for key, op in [("above", ">"), ("below", "<")]:
                if key not in options:
                    continue
                limit = options[key]
                if isinstance(limit, str) and re.fullmatch(
                    r"[a-z_][a-z0-9_]*\.[a-z0-9_]+", limit
                ):
                    limit = f"(states({json.dumps(limit)}) | float(none))"
                    checks.append(f"({limit} is not none)")
                else:
                    try:
                        limit = float(limit)
                        if not math.isfinite(limit):
                            raise ValueError("Numeric bounds must be finite")
                    except (ValueError, TypeError) as error:
                        raise ValueError(
                            "Numeric conditions need numeric bounds or entity IDs"
                        ) from error
                checks.append(f"(({value} | float(0)) {op} {limit})")
            if len(checks) == 1:
                raise ValueError("Numeric conditions need above or below")
            expressions.append("(" + " and ".join(checks) + ")")
    return (
        "{{ "
        + (" or " if options.get("match") == "any" else " and ").join(expressions)
        + " }}"
    )


def templates(conditions: list) -> list[str]:
    result = []
    for config in conditions:
        if not isinstance(config, dict):
            raise TypeError("Each condition must be an object")
        if config.get("condition") in {"and", "or", "not"}:
            nested = config.get(
                "conditions", config.get("options", {}).get("conditions")
            )
            if not isinstance(nested, list) or not nested:
                raise ValueError("Logical conditions need a non-empty conditions list")
            result.extend(templates(nested))
        elif config.get("condition") != "time":
            result.append(condition_template(config))
        else:
            condition_template(config)
    return result


def filter_definition(hass, definition: dict) -> dict:
    from homeassistant.helpers.template import Template

    tracked = set()
    times = set()
    entities = set()

    def collect_times(conditions):
        for config in conditions:
            if config.get("enabled") is False:
                continue
            if config.get("condition") in {"and", "or", "not"}:
                collect_times(config.get("conditions", config.get("options", {}).get("conditions", [])))
            elif config.get("condition") == "time":
                times.add("00:00:00")
                for key in ("after", "before"):
                    value = config.get("options", config).get(key)
                    if value:
                        times.add(value if len(value) == 8 else value + ":00")
            elif config.get("condition") in {"state", "numeric_state"}:
                options = config.get("options", config)
                ids = options.get("entity_id", [])
                entities.update([ids] if isinstance(ids, str) else ids)
                for key in ("above", "below"):
                    value = options.get(key)
                    if isinstance(value, str) and re.fullmatch(r"[a-z_][a-z0-9_]*\.[a-z0-9_]+", value):
                        entities.add(value)
            elif config.get("condition") == "template":
                tracked.add(condition_template(config))

    def matches(config):
        kind = config.get("condition")
        if config.get("enabled") is False:
            return True
        if kind in {"and", "or", "not"}:
            values = [
                matches(c)
                for c in config.get(
                    "conditions", config.get("options", {}).get("conditions", [])
                )
            ]
            return (
                all(values)
                if kind == "and"
                else any(values)
                if kind == "or"
                else not any(values)
            )
        value = Template(condition_template(config), hass).async_render(
            parse_result=True
        )
        return value is True or str(value).lower() in {"true", "on", "yes", "1"}

    def visit(node):
        conditions = node.get("conditions", [])
        templates(conditions)
        if conditions:
            collect_times(conditions)
        visible = all(matches(config) for config in conditions)
        children_key = "items" if "items" in node else "children"
        if children_key in node:
            node[children_key] = [child for child in node[children_key] if visit(child)]
        return visible

    result = deepcopy(definition)
    if not visit(result["tree"]):
        result["tree"]["items"] = []
    result["_condition_templates"] = sorted(tracked)
    result["_condition_times"] = sorted(times)
    result["_condition_entities"] = sorted(entities)
    return result
