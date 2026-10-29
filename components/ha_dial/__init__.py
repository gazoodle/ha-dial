"""ESPHome component for one HA-owned Dial view."""

import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import display, font, touchscreen
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
    }
).extend(cv.COMPONENT_SCHEMA)


async def to_code(config):
    component = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(component, config)
    cg.add(component.set_device(config[CONF_DEVICE]))
    cg.add(component.set_display(await cg.get_variable(config[CONF_DISPLAY])))
    cg.add(component.set_font(await cg.get_variable(config[CONF_FONT])))
    if "touchscreen" in config:
        cg.add(component.set_touchscreen(await cg.get_variable(config["touchscreen"])))
