"""The panel exposes stored definitions only to administrators."""

import asyncio


def test_definitions_require_admin(integration):
    async def run():
        integration.data["stored_definitions"] = {"dial_one": {"pages": []}}
        integration.connection.user.is_admin = False
        await integration.code._ws_definitions(
            integration.hass, integration.connection, {"id": 1}
        )
        integration.connection.send_result.assert_not_called()
        integration.connection.send_error.assert_called_once()
        await integration.code._ws_configure(
            integration.hass, integration.connection,
            {"id": 3, "save": True, "device": "dial_one", "definition": {}},
        )
        assert integration.connection.send_error.call_count == 2
        integration.data["definition_store"].async_save.assert_not_awaited()
        integration.connection.user.is_admin = True
        await integration.code._ws_definitions(
            integration.hass, integration.connection, {"id": 2}
        )
        integration.connection.send_result.assert_called_once_with(
            2, {"dial_one": {"pages": []}}
        )

    asyncio.run(run())
