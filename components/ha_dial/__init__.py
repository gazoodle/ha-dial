"""ESPHome component for one HA-owned Dial view."""

import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import display, font, touchscreen
from esphome.components.esp32 import include_builtin_idf_component
from esphome.const import CONF_DISPLAY, CONF_FONT, CONF_ID

AUTO_LOAD = ["json", "web_server_base"]
DEPENDENCIES = ["api", "display", "wifi"]

CONF_DEVICE = "device"

ha_dial_ns = cg.esphome_ns.namespace("ha_dial")
HaDial = ha_dial_ns.class_("HaDial", cg.Component)

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(HaDial),
        cv.Required(CONF_DEVICE): cv.string_strict,
        cv.Required(CONF_DISPLAY): cv.use_id(display.Display),
        cv.Required(CONF_FONT): cv.use_id(font.Font),
        cv.Optional("touchscreen"): cv.use_id(touchscreen.Touchscreen),
        # How the Dial hands a turned value to HA. Real networks and devices differ, so these can be tuned.
        cv.Optional("value_settle", default="150ms"): cv.positive_time_period_milliseconds,
        cv.Optional("value_resend", default="1500ms"): cv.positive_time_period_milliseconds,
        cv.Optional("value_wait", default="10s"): cv.positive_time_period_milliseconds,
        cv.Optional("value_resends", default=3): cv.int_range(min=0, max=10),
    }
).extend(cv.COMPONENT_SCHEMA)


async def to_code(config):
    include_builtin_idf_component("esp_http_client")
    component = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(component, config)
    cg.add(component.set_device(config[CONF_DEVICE]))
    cg.add(component.set_display(await cg.get_variable(config[CONF_DISPLAY])))
    cg.add(component.set_font(await cg.get_variable(config[CONF_FONT])))
    cg.add(
        component.set_value_timings(
            config["value_settle"].total_milliseconds,
            config["value_resend"].total_milliseconds,
            config["value_wait"].total_milliseconds,
            config["value_resends"],
        )
    )
    if "touchscreen" in config:
        cg.add(component.set_touchscreen(await cg.get_variable(config["touchscreen"])))
