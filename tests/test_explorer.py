"""Explorer: the tree it builds from a home, what it leaves out, and how it lives beside the owner's pages."""

import asyncio
import json
import sys
from types import SimpleNamespace

import pytest


def controls(items):
    for item in items:
        if "children" in item:
            yield from controls(item["children"])
        else:
            yield item


def labels(items):
    return [item["label"] for item in items]


def fixture_home(explorer):
    floor, area, entity = explorer.Floor, explorer.Area, explorer.Entity
    return explorer.Home(
        floors=[floor("ground", "Ground", 0), floor("first", "First", 1)],
        areas=[area("kitchen", "Kitchen", "ground"), area("hall", "Hall", "ground"), area("study", "Study", "first"), area("shed", "Shed")],
        entities=[
            entity("light.kitchen_ceiling", "Kitchen Ceiling", "kitchen"),
            entity("light.hall", "Hall light", "hall"),
            entity("switch.study_fan", "Fan", "study"),
            entity("light.shed", "Shed light", "shed"),
            entity("sensor.outside", "Outside"),
        ],
    )


def build(explorer, home, **options):
    return explorer.explore(home, options, {"style": "NAV-LIST", "theme": "ember"})


def test_home_runs_floors_then_areas_then_entities(dial):
    explorer = dial.load("explorer")
    items, counts = build(explorer, fixture_home(explorer))
    assert labels(items) == ["First", "Ground", "Shed", "Other devices"], "highest floor first, then loose areas, then the rest"
    ground = items[1]["children"]
    assert labels(ground) == ["Hall", "Kitchen"]
    assert ground[1]["children"][0]["entity_id"] == "light.kitchen_ceiling"
    assert counts == {"shown": 5, "omitted": {}}


def test_a_home_without_floors_starts_at_areas(dial):
    explorer = dial.load("explorer")
    home = fixture_home(explorer)
    home.floors = []
    items, _ = build(explorer, home)
    assert labels(items) == ["Hall", "Kitchen", "Shed", "Study", "Other devices"]


def test_a_lone_floor_is_skipped_and_empty_levels_never_appear(dial):
    explorer = dial.load("explorer")
    home = fixture_home(explorer)
    home.floors = [*home.floors, explorer.Floor("loft", "Loft", 2)]  # A floor with nothing on it.
    home.areas = [*home.areas, explorer.Area("spare", "Spare", "first")]  # A room with nothing in it.
    items, _ = build(explorer, home)
    assert "Loft" not in labels(items)
    assert "Spare" not in labels(items[0]["children"])

    home.entities = [entity for entity in home.entities if entity.area_id == "kitchen"]
    items, _ = build(explorer, home)
    assert labels(items) == ["Kitchen"]


def test_an_empty_home_still_builds(dial):
    explorer = dial.load("explorer")
    assert build(explorer, explorer.Home()) == ([], {"shown": 0, "omitted": {}})


def room_of(explorer, *domains):
    entities = [explorer.Entity(f"{domain}.item_{n}", f"Item {n}", "kitchen") for n, domain in enumerate(domains)]
    return explorer.Home(areas=[explorer.Area("kitchen", "Kitchen")], entities=entities)


def test_a_room_of_eight_lists_directly_and_nine_splits_by_function(dial):
    explorer = dial.load("explorer")
    items, _ = build(explorer, room_of(explorer, *["light"] * 4, *["sensor"] * 4))
    assert all("entity_id" in item for item in items[0]["children"])

    items, _ = build(explorer, room_of(explorer, *["light"] * 4, *["sensor"] * 4, "fan"))
    room = items[0]["children"]
    assert labels(room) == ["Lights", "Item 8", "Sensors"], "a group of one stays in the room itself"
    assert len(room[0]["children"]) == 4


def test_many_of_one_kind_stay_one_long_page_rather_than_a_pointless_group(dial):
    explorer = dial.load("explorer")
    items, _ = build(explorer, room_of(explorer, *["light"] * 20))
    assert len(items[0]["children"]) == 20
    assert items[0]["style"] in dial.load("catalogue").PAGED_STYLES


def test_what_is_left_out_is_counted_by_reason(dial):
    explorer = dial.load("explorer")
    entity = explorer.Entity
    home = explorer.Home(
        entities=[
            entity("light.kept", "Kept"),
            entity("light.hidden", "Hidden", hidden=True),
            entity("light.off", "Off", disabled=True),
            entity("sensor.rssi", "RSSI", category="diagnostic"),
            entity("number.setting", "Setting", category="config"),
            entity("automation.morning", "Morning"),
            entity("light.unwanted", "Unwanted"),
        ]
    )
    items, counts = build(explorer, home, exclude=["light.unwanted"])
    assert [item["entity_id"] for item in controls(items)] == ["light.kept"]
    assert counts == {"shown": 1, "omitted": {"hidden": 1, "disabled": 1, "diagnostic": 2, "unsupported": 1, "excluded": 1}}


def test_assist_only_uses_saved_exposure(dial):
    explorer = dial.load("explorer")
    entity = explorer.Entity
    home = explorer.Home(entities=[entity("light.yes", "Yes", exposed=True), entity("light.no", "No", exposed=False), entity("light.unset", "Unset")])
    items, counts = build(explorer, home, assist_only=True)
    assert [item["entity_id"] for item in controls(items)] == ["light.yes"]
    assert counts["omitted"] == {"not_exposed": 2}
    assert len(list(controls(build(explorer, home)[0]))) == 3


def test_doors_and_locks_always_confirm_and_a_switch_leaves_them_out(dial):
    explorer = dial.load("explorer")
    entity = explorer.Entity
    home = explorer.Home(
        entities=[
            entity("cover.garage", "Garage", device_class="garage"),
            entity("cover.gate", "Gate", device_class="gate"),
            entity("cover.front", "Front door", device_class="door"),
            entity("cover.blind", "Blind", device_class="blind"),
            entity("lock.front", "Lock"),
            entity("alarm_control_panel.home", "Alarm"),
        ]
    )
    found = {item["entity_id"]: item for item in controls(build(explorer, home)[0])}
    assert {name for name, item in found.items() if item.get("confirm")} == {"cover.garage", "cover.gate", "cover.front", "lock.front", "alarm_control_panel.home"}

    items, counts = build(explorer, home, include_security=False)
    assert [item["entity_id"] for item in controls(items)] == ["cover.blind"]
    assert counts["omitted"] == {"security": 5}


@pytest.mark.parametrize("scope,expected", [({"floor_id": "ground"}, ["Hall", "Kitchen"]), ({"area_id": "kitchen"}, ["Ceiling"])])
def test_an_explorer_can_cover_one_floor_or_one_area(dial, scope, expected):
    explorer = dial.load("explorer")
    items, counts = build(explorer, fixture_home(explorer), **scope)
    assert labels(items) == expected
    assert counts["omitted"]["out_of_scope"] == 5 - counts["shown"]


def test_awkward_home_data_cannot_break_the_tree(dial):
    explorer = dial.load("explorer")
    definition = dial.load("definition")
    long_id = "light." + "x" * 200
    home = explorer.Home(
        floors=[explorer.Floor("f" * 100, "F" * 100, None, "hue:floor")],
        areas=[explorer.Area("a" * 100, "A" * 100, "f" * 100, "custom:room"), explorer.Area("b", "B")],
        entities=[
            explorer.Entity(long_id, "N" * 100, "a" * 100, "hue:bulb"),
            explorer.Entity("light.two", "Two", "b"),
            explorer.Entity("light.orphan", "Orphan", "deleted_area"),
        ],
    )
    items, _ = build(explorer, home)
    definition.validate_definition({"tree": {"id": "root", "title": "Home", "style": "NAV-LIST", "items": items}})
    assert "Other devices" in labels(items), "an entity whose area has gone is still reachable"
    assert {item["icon"] for item in controls(items)} == {"mdi:lightbulb"}


def test_numbered_names_sort_as_numbers(dial):
    explorer = dial.load("explorer")
    items, _ = build(explorer, room_of(explorer, *["sensor"] * 12))
    assert labels(items[0]["children"])[:3] == ["Item 0", "Item 1", "Item 2"]
    assert labels(items[0]["children"])[-1] == "Item 11"


def test_floors_show_their_own_level(dial):
    explorer = dial.load("explorer")
    items, _ = build(explorer, fixture_home(explorer))
    assert {item["label"]: item["icon"] for item in items[:2]} == {"First": "mdi:home-floor-1", "Ground": "mdi:home-floor-g"}


def test_a_room_name_is_not_repeated_inside_the_room(dial):
    explorer = dial.load("explorer")
    items, _ = build(explorer, fixture_home(explorer), area_id="kitchen")
    assert items[0]["label"] == "Ceiling"


def styles_in(items):
    return {item["id"]: item["style"] for item in items if "children" in item}


def test_a_page_of_eight_or_fewer_can_use_any_navigation_style(dial):
    explorer, catalogue = dial.load("explorer"), dial.load("catalogue")
    for style in catalogue.NAV_STYLES:
        assert explorer.page_style("x", 8, style, {}) == style


def test_a_page_over_eight_falls_back_rather_than_hiding_items(dial):
    explorer, catalogue = dial.load("explorer"), dial.load("catalogue")
    for style in catalogue.NAV_STYLES:
        expected = style if style in catalogue.PAGED_STYLES else "NAV-LIST"
        assert explorer.page_style("x", 9, style, {}) == expected
    assert explorer.page_style("x", 9, "NAV-ORBIT", {"long_style": "NAV-SNAKE"}) == "NAV-SNAKE"


def test_a_page_override_wins_and_still_cannot_hide_items(dial):
    explorer = dial.load("explorer")
    options = {"pages": {"x_area_kitchen": {"style": "NAV-ORBIT", "theme": "cobalt", "appearance": {"raster": "crisp"}}}, "random": True}
    home = room_of(explorer, "light", "light", "light")
    items, _ = build(explorer, home, **options)
    assert items[0]["style"] == "NAV-ORBIT"
    assert items[0]["theme"] == "cobalt"
    assert items[0]["appearance"] == {"raster": "crisp"}

    items, _ = build(explorer, room_of(explorer, *["light"] * 20), **options)
    assert items[0]["style"] == "NAV-LIST"


def test_random_is_stable_until_shuffled_and_shows_off_the_range(dial):
    explorer, catalogue = dial.load("explorer"), dial.load("catalogue")
    picks = [explorer.page_style(f"x_area_{n}", 5, "NAV-LIST", {"random": True}) for n in range(200)]
    assert picks == [explorer.page_style(f"x_area_{n}", 5, "NAV-LIST", {"random": True}) for n in range(200)]
    assert set(picks) == catalogue.NAV_STYLES, "every style gets its turn"

    moved = [explorer.page_style(f"x_area_{n}", 5, "NAV-LIST", {"random": True, "shuffle": 1}) for n in range(200)]
    assert moved != picks
    assert {explorer.page_style(f"x_area_{n}", 9, "NAV-LIST", {"random": True}) for n in range(200)} == catalogue.PAGED_STYLES


def test_generated_pages_inherit_the_explorers_look(dial):
    explorer = dial.load("explorer")
    items, _ = explorer.explore(fixture_home(explorer), {}, {"style": "NAV-SNAKE", "theme": "rose", "appearance": {"snake-twist": 20}})
    room = items[1]["children"][0]
    assert (room["style"], room["theme"], room["appearance"]) == ("NAV-SNAKE", "rose", {"snake-twist": 20})


@pytest.mark.parametrize(
    "options",
    [
        {"nonsense": 1},
        {"floor_id": "a", "area_id": "b"},
        {"assist_only": "yes"},
        {"shuffle": True},
        {"long_style": "NAV-ORBIT"},
        {"camera_style": "NAV-LIST"},
        {"picture_mode": "sepia"},
        {"exclude": ["not an entity"]},
        {"pages": {"x": {"style": "CHR-TRICOMPAX"}}},
        {"pages": {"x": {"nonsense": 1}}},
    ],
)
def test_bad_settings_are_refused(dial, options):
    with pytest.raises((TypeError, ValueError)):
        dial.load("explorer").validate_explorer(options)


def install_registries(dial, floors=(), areas=(), entries=(), devices=()):
    """Stand-ins shaped like HA's registries; a lookup that wrote a default would fail the test."""
    if "homeassistant" not in sys.modules:
        dial.module("homeassistant")
    helpers = sys.modules.get("homeassistant.helpers") or dial.module("homeassistant.helpers")

    class EntityRegistry:
        def __init__(self):
            self.entities = {entry.entity_id: entry for entry in entries}

        def async_update_entity_options(self, *_):
            raise AssertionError("Explorer must never change exposure settings")

    entity_registry = EntityRegistry()
    device_map = {device.id: device for device in devices}
    modules = {
        "floor_registry": {"async_get": lambda _: SimpleNamespace(async_list_floors=lambda: floors), "EVENT_FLOOR_REGISTRY_UPDATED": "floors"},
        "area_registry": {"async_get": lambda _: SimpleNamespace(async_list_areas=lambda: areas), "EVENT_AREA_REGISTRY_UPDATED": "areas"},
        "device_registry": {"async_get": lambda _: SimpleNamespace(async_get=device_map.get), "EVENT_DEVICE_REGISTRY_UPDATED": "devices"},
        "entity_registry": {"async_get": lambda _: entity_registry, "EVENT_ENTITY_REGISTRY_UPDATED": "entities"},
    }
    for name, attributes in modules.items():
        setattr(helpers, name, dial.module(f"homeassistant.helpers.{name}", **attributes))
    dial.module("homeassistant.helpers.start", async_at_started=lambda *_: lambda: None)
    return entity_registry


def entry(entity_id, **values):
    return SimpleNamespace(
        **{
            "entity_id": entity_id, "name": None, "original_name": None, "area_id": None, "device_id": None, "icon": None, "original_icon": None,
            "device_class": None, "original_device_class": None, "entity_category": None, "hidden_by": None, "disabled_by": None, "options": {},
            **values,
        }
    )


class States(dict):
    def async_all(self):
        return list(self.values())


def state(entity_id, **attributes):
    return SimpleNamespace(entity_id=entity_id, state="on", attributes=attributes)


def test_read_home_takes_what_it_needs_from_the_registries(dial):
    explorer = dial.load("explorer")
    install_registries(
        dial,
        floors=[SimpleNamespace(floor_id="g", name="Ground", level=0, icon=None)],
        areas=[SimpleNamespace(id="k", name="Kitchen", floor_id="g", icon=None)],
        devices=[SimpleNamespace(id="d1", area_id="k")],
        entries=[
            entry("light.a", original_name="A", device_id="d1"),
            entry("light.b", name="Named", area_id="k", options={"conversation": {"should_expose": True}}),
            entry("light.starting_up", area_id="k"),
            entry("sensor.c", entity_category=SimpleNamespace(value="diagnostic"), hidden_by="user", disabled_by="user"),
        ],
    )
    dial.module("homeassistant.exceptions", HomeAssistantError=Exception)
    dial.module("homeassistant.components")
    dial.module("homeassistant.components.homeassistant")
    dial.module("homeassistant.components.homeassistant.exposed_entities", async_get_entity_settings=lambda *_: {})
    hass = SimpleNamespace(states=States({"light.a": state("light.a", friendly_name="Friendly A"), "light.b": state("light.b"), "input_select.mode": state("input_select.mode", friendly_name="Mode")}))
    found = {entity.entity_id: entity for entity in explorer.read_home(hass).entities}
    assert found["light.a"].name == "Friendly A"
    assert found["light.a"].area_id == "k", "an entity without an area uses its device's"
    assert found["light.b"].name == "Named" and found["light.b"].exposed is True
    assert found["light.a"].exposed is None
    assert found["light.starting_up"].name == "Starting Up", "no state yet at HA's start, but it exists"
    assert (found["sensor.c"].category, found["sensor.c"].hidden, found["sensor.c"].disabled) == ("diagnostic", True, True)
    assert found["input_select.mode"].name == "Mode", "a helper with no registry entry still appears"


def own_pages(*extra):
    return [{"id": "home", "title": "Home", "entities": ["light.mine"]}, {"id": "mine", "title": "My page", "parent": "home"}, *extra]


def explorer_page(**options):
    return {"id": "explore", "title": "Explore", "parent": "home", "icon": "mdi:compass-outline", "explorer": options}


@pytest.fixture
def home_of_rooms(dial):
    install_registries(
        dial,
        areas=[SimpleNamespace(id=f"room_{n}", name=f"Room {n}", floor_id=None, icon=None) for n in range(12)],
        entries=[entry(f"light.l{n}", area_id=f"room_{n % 12}", name=f"Lamp {n}") for n in range(60)],
    )
    return SimpleNamespace(states=States())


def test_an_explorer_takes_one_slot_beside_the_owners_own_items(dial, home_of_rooms):
    definition = dial.load("definition")
    built = definition.build_definition(home_of_rooms, own_pages(explorer_page()), "ember")
    top = built["tree"]["items"]
    assert [item["label"] for item in top] == ["My page", "Explore", "Mine"]
    explore = next(item for item in top if item["id"] == "explore")
    assert len(explore["children"]) == 12, "more than eight rooms, on a page that scrolls"
    assert explore["style"] == "NAV-LIST"
    assert built["tree"]["style"] == "NAV-ORBIT", "the owner's own page keeps its own style"


def test_the_slot_counts_against_the_owners_page(dial, home_of_rooms):
    definition = dial.load("definition")
    full = [{"id": f"p{n}", "title": f"Page {n}", "parent": "home"} for n in range(7)]
    with pytest.raises(ValueError, match="at most 8"):
        definition.build_definition(home_of_rooms, [*own_pages(), *full, explorer_page()], "ember")


@pytest.mark.parametrize("kind", ["pages", "controls", "both"])
def test_a_hand_built_page_can_go_past_eight_in_a_style_that_scrolls(dial, kind):
    definition, catalogue = dial.load("definition"), dial.load("catalogue")
    hass = SimpleNamespace(states={})
    entities = [f"light.l{n}" for n in range(12 if kind == "controls" else 6 if kind == "both" else 0)]
    subpages = [{"id": f"p{n}", "title": f"Page {n}", "parent": "home"} for n in range(12 if kind == "pages" else 6 if kind == "both" else 0)]
    for style in catalogue.PAGED_STYLES:
        built = definition.build_definition(hass, [{"id": "home", "title": "Home", "style": style, "entities": entities}, *subpages], "ember")
        assert len(built["tree"]["items"]) == 12
    with pytest.raises(ValueError, match="scrolls or pages"):
        definition.build_definition(hass, [{"id": "home", "title": "Home", "style": "NAV-ORBIT", "entities": entities}, *subpages], "ember")


def picture_home(explorer):
    return explorer.Home(entities=[explorer.Entity("camera.gate", "Gate"), explorer.Entity("image.drive", "Drive"), explorer.Entity("light.a", "A")])


def test_cameras_use_the_chosen_style_and_treatment(dial):
    explorer = dial.load("explorer")
    items = {item["entity_id"]: item for item in controls(build(explorer, picture_home(explorer), camera_style="CAM-RADAR", picture_mode="dither")[0])}
    for entity in ("camera.gate", "image.drive"):
        assert items[entity]["style"] == "CAM-RADAR"
        assert items[entity]["appearance"] == {"picture-mode": "dither"}
    assert "appearance" not in items["light.a"] and not items["light.a"]["style"].startswith("CAM-")


def test_cameras_keep_their_defaults_when_nothing_is_chosen(dial):
    explorer = dial.load("explorer")
    camera = next(item for item in controls(build(explorer, picture_home(explorer))[0]) if item["entity_id"] == "camera.gate")
    assert camera["style"] == "CAM-PORTAL" and "appearance" not in camera


def test_a_generated_camera_reaches_its_picture_in_the_chosen_style(dial):
    explorer, definition, frames = dial.load("explorer"), dial.load("definition"), dial.load("frames")
    items, _ = build(explorer, picture_home(explorer), camera_style="CAM-CINEMA", picture_mode="mono")
    definition.validate_definition({"tree": {"id": "r", "title": "Home", "style": "NAV-LIST", "items": items}})
    navigator = dial.load("navigator").Navigator(definition={"tree": {"id": "r", "title": "Home", "style": "NAV-LIST", "items": items}})
    navigator.input("touch", "x_other")
    navigator.input("touch", "camera.gate")
    view = navigator.current()
    assert view["style"] == "CAM-CINEMA"
    key = frames.frame_key(view)
    assert key is not None and "camera.gate" in key and "mono" in key


def test_the_explorer_page_uses_its_own_style_while_it_fits(dial):
    definition = dial.load("definition")
    install_registries(dial, areas=[SimpleNamespace(id="a", name="A", floor_id=None, icon=None)], entries=[entry("light.a", area_id="a")])
    hass = SimpleNamespace(states=States())
    page = {**explorer_page(), "style": "NAV-PETALS"}
    built = definition.build_definition(hass, [*own_pages(), page], "ember")
    assert next(item for item in built["tree"]["items"] if item["id"] == "explore")["style"] == "NAV-PETALS"


def test_the_item_limit_now_follows_the_style(dial):
    definition = dial.load("definition")
    items = [{"id": f"i{n}", "label": f"Item {n}", "children": []} for n in range(9)]
    definition.validate_definition({"tree": {"id": "r", "title": "T", "style": "NAV-LIST", "items": items}})
    with pytest.raises(ValueError, match="at most 8"):
        definition.validate_definition({"tree": {"id": "r", "title": "T", "style": "NAV-ORBIT", "items": items}})


@pytest.mark.parametrize("style", ["NAV-LIST", "NAV-GRID", "NAV-SNAKE", "NAV-COMPASS", "NAV-RIBBON", "NAV-ROLODEX", "NAV-PAGER"])
@pytest.mark.parametrize("raster", ["smooth", "crisp"])
def test_every_paged_style_shows_the_selection_on_a_huge_page(dial, style, raster):
    """The claim these styles are allowed on: a long page can't hide what you've turned to."""
    scene = dial.load("scene")
    items = [{"id": f"p{n}", "label": f"Page {n}", "icon": "mdi:folder"} for n in range(200)]
    for selected in (0, 1, 7, 8, 9, 57, 198, 199):
        resolved = scene.compile_scene({"kind": "menu", "id": "h", "title": "Home", "style": style, "back": True, "items": items, "selected": selected, "appearance": {"raster": raster}})
        assert f"p{selected}" in {region["id"] for region in resolved["regions"]}, (style, selected)
        assert len(resolved["elements"]) <= 64, (style, selected)
        assert len(resolved["regions"]) <= 16, (style, selected)
        assert len(json.dumps({"scene": resolved, "previous": resolved}, separators=(",", ":"))) <= scene.MAX_VIEW_BYTES, (style, selected)


def wired_home(integration, dial):
    rooms = {"entries": [entry("light.a", area_id="a", name="A"), entry("light.b", area_id="b", name="B")]}
    areas = [SimpleNamespace(id="a", name="Room A", floor_id=None, icon=None), SimpleNamespace(id="b", name="Room B", floor_id=None, icon=None)]
    registry = install_registries(dial, areas=areas, entries=rooms["entries"])
    listeners = {}

    def listen(event, callback):
        listeners[event] = callback
        return lambda: listeners.pop(event)

    later = []

    def call_later(_hass, _delay, callback):
        later.append(callback)
        return lambda: later.remove(callback)

    sys.modules["homeassistant.helpers.event"].__dict__["async_call_later"] = call_later
    integration.hass.states = States()
    integration.hass.bus = SimpleNamespace(async_listen=listen)
    integration.hass.is_running = True
    return SimpleNamespace(registry=registry, listeners=listeners, later=later, areas=areas)


def test_registry_changes_rebuild_settling_bursts_and_stop_with_the_dial(integration, dial):
    wired = wired_home(integration, dial)

    async def run():
        source = {"pages": own_pages(explorer_page())}
        runtime = integration.code.runtime
        definition = runtime._render_definition(integration.hass, source)
        await runtime._install_definition(integration.hass, "dial", source, definition)
        navigator = integration.data["navigators"]["dial"]
        navigator.input("touch", "explore")
        navigator.input("touch", "x_area_b")
        assert navigator.current()["title"] == "Room B"
        assert set(wired.listeners) == {"areas", "devices", "entities", "floors"}

        # A burst leaves one rebuild waiting.
        for _ in range(5):
            wired.listeners["entities"]({})
        assert len(wired.later) == 1

        # Room B is emptied, so the Dial returns to the nearest page that still exists.
        wired.registry.entities.pop("light.b")
        wired.later.pop()(None)
        await asyncio.gather(*integration.tasks)
        current = integration.data["navigators"]["dial"].current()
        assert current["title"] == "Explore"
        assert [item["id"] for item in current["items"]] == ["x_area_a"]

        # A change that makes no difference doesn't replace the navigator.
        before = integration.data["navigators"]["dial"]
        wired.listeners["devices"]({})
        wired.later.pop()(None)
        assert integration.data["navigators"]["dial"] is before

        wired.listeners["entities"]({})
        integration.data["explorer_unsubs"].pop("dial")()
        assert not wired.listeners and not wired.later, "nothing is left listening or waiting"

    asyncio.run(run())


def test_a_hand_built_dial_doesnt_listen_to_the_registries(integration, dial):
    wired = wired_home(integration, dial)

    async def run():
        source = {"pages": own_pages()}
        runtime = integration.code.runtime
        definition = runtime._render_definition(integration.hass, source)
        await runtime._install_definition(integration.hass, "dial", source, definition)
        assert not wired.listeners

    asyncio.run(run())
