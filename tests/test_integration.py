import asyncio
import json
from types import SimpleNamespace

SOURCE = {
    "theme": "ember",
    "pages": [
        {"id": "root", "title": "Home"},
        {"id": "room", "title": "Room", "parent": "root", "lights": ["light.example"]},
        {"id": "empty", "title": "Empty", "parent": "root"},
    ],
}


def test_reset_one_device_clears_configuration_and_blocks_old_inputs(integration):
    async def run():
        i = integration
        await i.code._ws_configure(i.hass, i.connection, {"id": 1, "device": "dial_one", "definition": SOURCE})
        await i.code._ws_configure(i.hass, i.connection, {"id": 2, "device": "dial_two", "definition": SOURCE})
        i.connection.user.is_admin = False
        await i.code._ws_reset(i.hass, i.connection, {"id": 3, "device": "dial_one"})
        assert i.connection.send_error.call_args.args[1] == "unauthorized"
        assert i.data["stored_definitions"]["dial_one"] == SOURCE
        i.connection.user.is_admin = True
        await i.code._ws_reset(i.hass, i.connection, {"id": 4, "device": "dial_one"})
        assert i.data["stored_definitions"] == {"dial_one": None, "dial_two": SOURCE}
        assert "dial_one" not in i.data["navigators"]
        assert json.loads(i.hass.services.async_call.call_args.args[2]["view"])["clear"] is True
        assert i.connection.send_result.call_args.args == (4, {"cleared": True})
        i.hass.services.async_call.reset_mock()
        assert await i.code._input(i.hass, "dial_one", "ready") == {}
        i.hass.services.async_call.assert_not_called()
        await i.code._ws_definitions(i.hass, i.connection, {"id": 5})
        assert i.connection.send_result.call_args.args[1] == {"dial_two": SOURCE}
        await i.code._ws_configure(i.hass, i.connection, {"id": 6, "device": "dial_one", "definition": SOURCE})
        assert i.data["stored_definitions"]["dial_one"] == SOURCE

    asyncio.run(run())


def test_reset_offline_device_and_storage_failure(integration):
    async def run():
        i = integration
        i.data["stored_definitions"] = {"dial_one": SOURCE}
        i.data["definition_store"].async_save.side_effect = OSError("disk full")
        try:
            await i.code._ws_reset(i.hass, i.connection, {"id": 1, "device": "dial_one"})
        except OSError:
            pass
        else:
            raise AssertionError("storage failure must propagate")
        assert i.data["stored_definitions"]["dial_one"] == SOURCE
        assert not i.data["resetting"]
        i.data["definition_store"].async_save.side_effect = None
        i.data["transport_available"] = {"dial_one": False}
        await i.code._ws_reset(i.hass, i.connection, {"id": 2, "device": "dial_one"})
        assert i.connection.send_result.call_args.args == (2, {"cleared": False})
        assert i.data["stored_definitions"]["dial_one"] is None

    asyncio.run(run())


def test_draft_isolation_saved_deployment_and_invalid_save(integration):
    async def run():
        i = integration
        await i.code._ws_configure(
            i.hass,
            i.connection,
            {"id": 1, "device": "preview_demo", "definition": SOURCE},
        )
        assert not i.data["stored_definitions"]
        await i.code._input(i.hass, "preview_demo", "press")
        await i.code._input(i.hass, "preview_demo", "press")
        await i.code._input(i.hass, "preview_demo", "rotate_right")
        assert i.code._navigator(i.hass, "preview_demo").current()["value"] == 55
        i.hass.services.async_call.assert_not_called()
        await i.code._ws_configure(
            i.hass, i.connection, {"id": 2, "device": "demo_dial", "definition": SOURCE}
        )
        assert i.data["stored_definitions"]["demo_dial"] == SOURCE
        assert (
            json.loads(i.hass.services.async_call.call_args.args[2]["view"])["revision"]
            > 0
        )
        await i.code._input(i.hass, "demo_dial", "press")
        page_id = i.code._navigator(i.hass, "demo_dial").view_id
        await i.code._ws_configure(
            i.hass, i.connection, {"id": 3, "device": "demo_dial", "definition": SOURCE}
        )
        assert i.code._navigator(i.hass, "demo_dial").view_id == page_id
        await i.code._ws_configure(
            i.hass,
            i.connection,
            {"id": 4, "device": "demo_dial", "definition": {"pages": []}},
        )
        assert i.connection.send_error.call_args.args[1] == "invalid_format"
        assert i.data["stored_definitions"]["demo_dial"] == SOURCE

    asyncio.run(run())


def test_template_macros_native_updates_and_back_location(integration):
    async def run():
        i = integration
        i.hass.templates["demo.jinja"] = (
            "{% macro tree(title, theme) %}{{ {'tree': {'id': 'home', 'title': title, 'theme': theme, 'items': []}} | tojson }}{% endmacro %}"
        )
        source = {
            "theme": "cobalt",
            "pages": [{"title": "Demo"}],
            "template": "{% from 'demo.jinja' import tree %}{{ tree(pages[0].title, theme) }}",
        }
        await i.code._ws_configure(
            i.hass,
            i.connection,
            {"id": 1, "device": "preview_macro", "definition": source},
        )
        assert i.data["definitions"]["preview_macro"]["tree"]["title"] == "Demo"
        callback = i.trackers[0].callback
        for result in (
            {"tree": {"id": "home", "title": "Changed", "items": []}},
            json.dumps({"tree": {"id": "home", "title": "JSON", "items": []}}),
        ):
            callback(None, [SimpleNamespace(result=result)])
            await asyncio.gather(*i.tasks)
            i.tasks.clear()
        assert i.code._navigator(i.hass, "preview_macro").current()["title"] == "JSON"
        i.hass.services.async_call.assert_not_called()

    asyncio.run(run())


def test_subscription_cleanup_and_scene_push(integration):
    async def run():
        i = integration
        await i.code._ws_configure(
            i.hass,
            i.connection,
            {"id": 1, "device": "preview_session", "definition": SOURCE},
        )
        events = []
        i.connection.send_event = lambda _, result: events.append(result)
        await i.code._ws_subscribe(
            i.hass, i.connection, {"id": 2, "device": "preview_session"}
        )
        await i.code._input(i.hass, "preview_session", "press")
        assert events[-1]["scene"]["label"] == "Room"
        assert events[-1]["revision"] > events[0]["revision"]
        i.connection.subscriptions[2]()
        assert "preview_session" not in i.data["navigators"]
        assert not i.watches

    asyncio.run(run())


def test_switch_cover_capabilities_services_and_preview(integration):
    async def run():
        i = integration
        i.hass.states.update(
            {
                "switch.demo": SimpleNamespace(state="off", attributes={}),
                "cover.demo": SimpleNamespace(
                    state="open",
                    attributes={"supported_features": 15, "current_position": 40},
                ),
                "cover.basic": SimpleNamespace(
                    state="closed", attributes={"supported_features": 3}
                ),
            }
        )
        source = {
            "pages": [
                {
                    "id": "root",
                    "title": "Home",
                    "entities": ["switch.demo", "cover.demo", "cover.basic"],
                }
            ]
        }
        for device in ("preview_domains", "demo_domains"):
            await i.code._ws_configure(
                i.hass, i.connection, {"id": 1, "device": device, "definition": source}
            )
            await i.code._input(i.hass, device, "touch", "switch.demo")
            i.hass.services.async_call.reset_mock()
            view = await i.code._input(i.hass, device, "rotate_right", push=False)
            assert view["value"] == 0
            i.hass.services.async_call.assert_not_called()
            await i.code._input(i.hass, device, "press", push=False)
            if device.startswith("preview"):
                i.hass.services.async_call.assert_not_called()
            else:
                i.hass.services.async_call.assert_awaited_once_with(
                    "switch", "turn_on", {"entity_id": "switch.demo"}
                )
            await i.code._input(i.hass, device, "back")
            await i.code._input(i.hass, device, "touch", "cover.demo")
            i.hass.services.async_call.reset_mock()
            view = await i.code._input(i.hass, device, "rotate_right", push=False)
            assert view["value"] == 45
            for action, item in (
                ("press", None),
                ("touch", "open"),
                ("touch", "close"),
            ):
                await i.code._input(i.hass, device, action, item, push=False)
            if device.startswith("preview"):
                i.hass.services.async_call.assert_not_called()
                assert i.code._navigator(i.hass, device).current()["value"] == 0
                assert i.code._navigator(i.hass, device).current()["state"] == "closed"
            else:
                assert [
                    (call.args[0], call.args[1])
                    for call in i.hass.services.async_call.await_args_list
                ] == [
                    ("cover", "set_cover_position"),
                    ("cover", "stop_cover"),
                    ("cover", "open_cover"),
                    ("cover", "close_cover"),
                ]
            await i.code._input(i.hass, device, "back")
            await i.code._input(i.hass, device, "touch", "cover.basic")
            i.hass.services.async_call.reset_mock()
            for action, item in (
                ("rotate_right", None),
                ("set_value", None),
                ("press", None),
                ("touch", "stop"),
                ("touch", "invalid"),
            ):
                view = await i.code._input(i.hass, device, action, item, 90, push=False)
            assert not view["continuous"] and not view["pending"]
            i.hass.services.async_call.assert_not_called()
            i.hass.states["cover.basic"].state = "unavailable"
            # A state push resynchronises capabilities and availability.
            for entities, watcher in i.watches:
                if "cover.basic" in entities:
                    await watcher(SimpleNamespace(data={"entity_id": "cover.basic"}))
            i.hass.services.async_call.reset_mock()
            await i.code._input(i.hass, device, "touch", "open", push=False)
            i.hass.services.async_call.assert_not_called()
            i.hass.states["cover.basic"].state = "closed"

    asyncio.run(run())


def test_burst_coalesces_scenes_and_commands_do_not_wait_for_display(integration):
    async def run():
        i = integration
        await i.code._ws_configure(
            i.hass,
            i.connection,
            {"id": 1, "device": "burst_dial", "definition": SOURCE},
        )
        await i.code._input(i.hass, "burst_dial", "press")
        await i.code._input(i.hass, "burst_dial", "press")
        started, release = asyncio.Event(), asyncio.Event()
        frames, commands = [], []

        async def call(domain, service, data, **kwargs):
            if domain == "esphome":
                frames.append(json.loads(data["view"]))
                if len(frames) == 1:
                    started.set()
                    await release.wait()
            else:
                commands.append(data["brightness_pct"])

        i.hass.services.async_call.side_effect = call
        first = asyncio.create_task(
            i.code._input(
                i.hass, "burst_dial", "set_value", value=60, input_sequence=10
            )
        )
        await started.wait()
        rest = [
            asyncio.create_task(
                i.code._input(
                    i.hass,
                    "burst_dial",
                    "set_value",
                    value=value,
                    input_sequence=sequence,
                )
            )
            for sequence, value in ((11, 65), (12, 70), (13, 75))
        ]
        # A marker task runs after all the input tasks have reached their first await.
        marker = asyncio.Event()
        asyncio.get_running_loop().call_soon(marker.set)
        await marker.wait()
        assert commands == [60, 65, 70, 75], (
            "commands must be issued before a blocked display send"
        )
        assert len(frames) == 1
        release.set()
        await asyncio.gather(first, *rest)
        assert [frame["value"] for frame in frames] == [60, 75], (
            "intermediate scenes must be replaced"
        )
        assert frames[-1]["input_sequence"] == 13
        assert not i.data["pending_scenes"] and not i.data["scene_workers"]
        await i.code._input(
            i.hass, "burst_dial", "set_value", value=5, input_sequence=12
        )
        assert commands[-1] == 75, "stale input must not replay"

    asyncio.run(asyncio.wait_for(run(), 2))


def test_state_confirmation_retains_target_until_confirmed_and_service_failure_clears_it(
    integration,
):
    async def run():
        i = integration
        await i.code._ws_configure(
            i.hass,
            i.connection,
            {"id": 1, "device": "feedback_dial", "definition": SOURCE},
        )
        await i.code._input(i.hass, "feedback_dial", "press")
        await i.code._input(i.hass, "feedback_dial", "press")
        await i.code._input(
            i.hass, "feedback_dial", "set_value", value=80, input_sequence=10
        )
        navigator = i.code._navigator(i.hass, "feedback_dial")
        navigator.sync(60, True, True, continuous=True)
        assert navigator.current()["value"] == 80
        assert navigator.current()["confirmed_value"] == 60
        assert navigator.current()["pending"]
        navigator.sync(80, True, True, continuous=True)
        assert not navigator.current()["pending"]
        from homeassistant.exceptions import HomeAssistantError

        async def fail(domain, *_args, **_kwargs):
            if domain == "light":
                raise HomeAssistantError("Demo action failed")

        i.hass.services.async_call.side_effect = fail
        import pytest

        with pytest.raises(HomeAssistantError, match="Demo action failed"):
            await i.code._input(
                i.hass, "feedback_dial", "set_value", value=90, input_sequence=11
            )
        assert not navigator.current()["pending"]
        assert navigator.current()["value"] == 50

    asyncio.run(run())


def test_immediate_eager_delivery_does_not_leave_a_finished_worker_cached(integration):
    async def run():
        i = integration
        from homeassistant.exceptions import HomeAssistantError

        def create_task(coroutine, *, eager_start=True):
            task = asyncio.Task(
                coroutine, loop=asyncio.get_running_loop(), eager_start=eager_start
            )
            i.tasks.append(task)
            return task

        # Match HA's eager task scheduling, including a failure before the first yield.
        i.hass.async_create_task = create_task
        i.hass.services.async_call.side_effect = HomeAssistantError(
            "Demo transport not connected"
        )
        message = {"id": 1, "device": "demo_dial", "definition": SOURCE}
        await i.code._ws_configure(i.hass, i.connection, message)
        assert not i.data["scene_workers"], (
            "completed eager worker must not block future sends"
        )
        assert i.data["deployment_status"]["demo_dial"] == "failed"
        i.hass.services.async_call.side_effect = None
        await i.code._ws_configure(i.hass, i.connection, message)
        assert i.hass.services.async_call.await_count == 2
        assert not i.data["scene_workers"] and not i.data["pending_scenes"]
        assert i.data["deployment_status"]["demo_dial"] == "sent"

    asyncio.run(run())
