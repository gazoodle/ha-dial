# M5Dial Controller for Home Assistant

A beautiful, dynamically assigned physical control surface for Home Assistant.

Home Assistant chooses what the Dial controls. The Dial chooses the right interaction and presentation for it.

Turn it. Press it. Done.

> Status: first deployable page tree with NAV-ORBIT menus and light, switch and cover instruments

The rendering and interaction boundaries are defined in [ARCHITECTURE.md](ARCHITECTURE.md).

## The idea

M5Dial projects support a range of interface and deployment models. This project focuses on one control at a time, assigned dynamically by Home Assistant:

```text
Home Assistant selects an entity and control profile
                         ↓
             Dial displays its current state
                         ↓
               turn / press / touch
                         ↓
             command goes back to HA
                         ↓
               HA returns confirmed state
```

Examples:

- Walk into the kitchen and the Dial controls the kitchen speaker.
- Start watching television and it controls TV volume.
- Select the living-room thermostat from the Dial itself.
- Assign a light from an automation or dashboard.
- Show a temperature sensor as a read-only ambient display.
- Return to a quiet clock when nothing is assigned.

Changing the controlled entity must never require recompiling the firmware.

## Goals

- Excellent UX designed specifically for the M5Dial’s round display and physical encoder.
- Dynamic entity assignment from Home Assistant.
- A small set of polished, reusable control profiles.
- Immediate visual feedback while turning the dial.
- Honest disconnected, unavailable and pending states.
- Local Home Assistant operation with no cloud dependency.
- Simple standalone installation for any Home Assistant setup.
- A protocol that other Home Assistant tools can drive.

## Non-goals

- A multi-page Lovelace dashboard running on the Dial.
- Displaying every entity or capability Home Assistant exposes.
- Replicating the full Lovelace interface on a 240 × 240 screen.
- Inventing an interface for every possible entity.
- Requiring a particular Home Assistant setup or companion project.
- Storing a powerful Home Assistant access token on the Dial.
- Supporting several hardware families before the M5Dial experience is right.

## Control profiles

The visual and physical interaction is selected by a control profile, not merely by the Home Assistant domain.

| Profile | Turn | Press | Additional control |
| --- | --- | --- | --- |
| `dimmer` | Set brightness | Toggle | Colour or colour temperature |
| `thermostat` | Set target temperature | Toggle HVAC | Select mode |
| `volume` | Set volume | Mute | Play/pause |
| `seek` | Nudge position | Play/pause | Previous/next |
| `selector` | Move through options | Select | Long press to leave |
| `position` | Set cover position | Stop | Open/close |
| `toggle` | — | Toggle | — |
| `readout` | — | — | Show sensor detail |

Home Assistant may infer a sensible default profile from an entity’s domain and supported features, but callers can explicitly choose another profile.

A `media_player`, for example, might use `volume`, `seek` or `selector`.

## Interaction model

### Focused control

When an entity is assigned:

- The outer arc communicates its current value and range.
- The centre shows the primary value or state.
- The entity name remains short and readable.
- Turning changes the primary value.
- Pressing performs the profile’s primary action.
- Touch exposes only controls that cannot be expressed naturally by the dial.
- Long press leaves the current interaction.

The display updates immediately while the user turns. Home Assistant updates are throttled, and confirmed state is reconciled without visually jumping backwards.

### Entity picker

Home Assistant can provide an ordered list of favourite entities.

- Turn to move through the list.
- Press to select.
- Long press to leave.
- Only explicitly selected or labelled entities appear.

The picker is not a browser for every entity in the home.

### Idle

When no entity is assigned, the Dial shows a restrained clock or ambient readout before dimming or sleeping.

## UX principles

The physical dial is the interface. The screen explains it.

- One control fills the screen.
- Navigation stays out of the way.
- Names stay short enough to read without scrolling.
- Motion helps explain changes.
- Colour communicates state.
- Every encoder detent produces immediate feedback.
- Touch targets remain comfortably large.
- The same gesture means the same thing across profiles.
- Unavailable and disconnected states are unmistakable.
- The common action is always the easiest action.

The outer on-screen arc should visually meet the physical encoder surrounding it.

## Architecture

The project contains both halves of the product:

```text
Card editor template + Home Assistant state
                         │
                         ▼
             HA page tree and navigator
                         │
                         ▼
              HA scene compiler
                ┌────────┴────────┐
                ▼                 ▼
          Card canvas       ESPHome renderer
```

The integration owns the complete navigation tree, page themes and scene geometry. The editor supports Jinja templates for reusable tree macros. Menus use `NAV-ORBIT`; controls use `CTL-LIGHT-INSTRUMENT`, `CTL-SWITCH-INSTRUMENT` or `CTL-COVER-INSTRUMENT`. The preview canvas and Dial consume the same resolved scene.

Other Home Assistant tools may use the public protocol in the future, but the project does not depend on them.

## Protocol model

### Chronograph pages

Choose `CHR-TRICOMPAX`, `CHR-WORLDTIMER`, `CHR-SKELETON` or `CHR-MOONPHASE` in a page's
Atlas gallery. Clock options live in the appearance dialog's Options tab. A blank clock time
zone uses HA's configured local time; explicit zones use IANA names and include daylight saving.
Worldtimer accepts two to eight zones. Its optional power reserve sensor must report `%` in
the range 0–100. Moonphase accepts a Moon integration sensor. Missing, unavailable or invalid
complication readings display an unavailable indication; they never receive sample readings.

```yaml
pages:
  - id: time
    title: Time
    style: CHR-WORLDTIMER
    clock:
      timezone: UTC
      world_zones: [Europe/London, America/New_York, Asia/Tokyo, Australia/Sydney]
      reserve_entity: sensor.example_reserve
      moon_entity: sensor.example_moon
```

Tricompax shows a 24-hour register, small seconds and a day-of-month register. Skeleton uses
separate hour, minute and second registers. Moonphase replaces the date register with the
selected sensor's phase. Turn to select a configured destination and press to enter it; Back
and Home retain their normal meaning. Without destinations, the face shows the date.

HA resolves clock time and geometry on scheduled second boundaries and uses the existing
coalescing scene publisher. This is a clock deadline, not state polling. Leaving the face
stops clock scene delivery; replacing its definition, closing a preview or unloading the server
removes its time/state subscriptions. Browser and Dial receive the same resolved clock reading.
These faces require firmware with scene v4 support (private build b3 or later).

Home Assistant sends a resolved scene containing only what the Dial needs: final geometry,
theme colours, compact antialiased text masks and touch regions. The definition and navigation
tree remain in Home Assistant. For example, the scene's drawing instructions use:

```json
{"revision":1,"scene":{"version":1,"screen":"home","width":240,"height":240,"background":"#060707",
 "elements":[{"op":"circle","x":120,"y":120,"r":116,"stroke":"#ff8b2d"}],
 "regions":[{"id":"light.example","x":120,"y":36,"r":22}]}}
```

The Dial returns semantic navigation and control intents:

```json
{"device":"ha_dial","action":"set_value","value":21.0}
```

Home Assistant remains responsible for translating those intents into domain actions.

## Target for the first usable release

The current first release supports:

- M5Stack Dial v1.1.
- Wi-Fi provisioning.
- Encrypted ESPHome API.
- OTA updates.
- Rotary encoder, push button, touch, display and backlight.
- Multi-level page trees with light, switch and cover controls at the leaves.
- Per-page Atlas theme selection.
- `NAV-ORBIT` navigation and `CTL-LIGHT-INSTRUMENT` light controls.
- HA Jinja templates with state tracking and reusable macros.
- One resolved scene shared by the dashboard card and ESPHome renderer.

Other Atlas concepts remain outside this first release.

## Definition of good

The first version is successful when:

- Changing the controlled entity never requires a firmware rebuild.
- The displayed value reacts immediately to every encoder detent.
- An externally changed HA state appears promptly on the Dial.
- Losing HA cannot leave a control looking live.
- Each supported profile is understandable without instructions.
- The picker remains pleasant with at least twenty configured entities.
- The interface feels coherent and intentionally designed.
- The device can be installed in any Home Assistant setup.

## Hardware

Initial target:

- M5Stack Dial v1.1
- ESP32-S3
- 240 × 240 GC9A01A round display
- FT5x06 capacitive touch controller
- Rotary encoder and front button
- Display backlight
- Buzzer
- PCF8563 RTC
- RC522-compatible NFC hardware

NFC and the RTC are not required for the first control prototype.

Hardware definitions should begin with M5Stack’s current ESPHome configuration:

- https://docs.m5stack.com/en/homeassistant/devices/dial
- https://devices.esphome.io/devices/m5stack-dial/

## Prototype firmware

Firmware and HA Dial Server now have independent calendar versions. See
[Versioning](#versioning) for the sources and bump commands. ESPHome exposes **Firmware Version**
as a diagnostic text sensor; project metadata and the startup screen use the same value.

The first USB prototype displays **Hello** in the centre and moves a pointer around the edge as the encoder turns. It deliberately has no Wi-Fi, Home Assistant API or device-specific configuration yet.

The connected prototype is `firmware/ha-dial-connected.yaml`. It adds the reusable external component, native API, OTA updates, encoder button and FT5x06 touch input. The HA integration binds its navigation to one configured light: turning sets brightness, pressing toggles power, and external state changes return to both the card and Dial. The base hardware test remains network-free.

```shell
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest -q
tools/compile
tools/compile ha-dial-connected.yaml
```

## Prototype installation

The development host serves the repository to ESPHome and mirrors the integration and card directly into the mounted Home Assistant config folder. The default is `/Volumes/config`; set `HA_CONFIG` when the mount lives elsewhere.

```shell
tools/serve
```

On the first deployment, restart Home Assistant manually, then follow [Getting started](#getting-started). Add **HA Dial Server** once for all Dials; each **HA Dial** dashboard card configures one Dial. Later integration updates raise a restart Repair. The optional advanced template field supports reusable Jinja macros. This example builds Home → Ground floor → Office → a light:

```yaml
type: custom:ha-dial-card
device: ha_dial
theme: ember
template: |
  {% set ns = namespace(lights=[]) %}
  {% macro light(entity, label) -%}
    {% set ns.lights = ns.lights + [{'id': entity, 'label': label,
      'entity_id': entity, 'profile': 'dimmer', 'style': 'CTL-LIGHT-INSTRUMENT'}] %}
  {%- endmacro %}
  {% set _ = light('light.example', 'Desk') %}
  {{ {'tree': {'id': 'home', 'title': 'Home', 'theme': theme,
    'style': 'NAV-ORBIT', 'items': [{'id': 'ground', 'label': 'Ground floor',
    'theme': 'verdant', 'children': [{'id': 'office', 'label': 'Office',
    'theme': 'cobalt', 'children': ns.lights}]}]}} | tojson }}
```

The underscore is the ESPHome service slug; the firmware node name remains `ha-dial`. Dashboard
editor drafts use a local preview navigator. The saved card compiles and deploys its current scene
when it is loaded outside the editor.
Later code changes write a content-based restart marker, including changes made without a
version bump, and the loaded integration raises a Repair.

To push an integration-only edit immediately without restarting the Git host:

```shell
python3 tools/deploy.py /Volumes/config
```

ESPHome can consume the component from the same development host:

```yaml
external_components:
  - source:
      type: git
      url: git://192.0.2.10:9421/ha-dial
      ref: fake-git-host
    components: [ha_dial]
```

For a browser-only view of the shared scene fixtures, run `.venv/bin/python -m http.server` in the
repository and open `http://localhost:8000/tools/card-preview.html`. Choose a theme and a navigation, light, switch or cover style. Configure and simulate the live navigation tree in the Home Assistant card editor.

The HA Dial Git proxy defaults to port **9421**, separate from the shared host's default. Set
`HA_DIAL_GIT_PORT` when starting `tools/serve` to override it and use that same port in the client's
Git URL. Each proxy instance serves this repository only.

Deploy to a provisioned device over OTA:

```shell
tools/flash ha-dial.local ha-dial-connected.yaml
```

For initial USB installation, check the detected serial port and flash it explicitly:

```shell
tools/flash /dev/cu.usbmodem…
tools/flash /dev/cu.usbmodem… ha-dial-connected.yaml
```

If the first flash cannot reset the Dial automatically, hold the StampS3’s G0 button while reconnecting USB, release it once powered, and run the command again.

The pointer geometry is kept independent of ESPHome and tested on the Mac by compiling and running a small C++ assertion program, following the same fast host-test pattern as ProxyStick.

## Development order

1. Confirm the exact device revision and flash a hardware test.
2. Bring up the display, encoder, button and touch.
3. Build one excellent simulated `dimmer` face.
4. Connect that face to a dynamically assigned Home Assistant light.
5. Establish target, command and state-update messages.
6. Add thermostat, volume and selector profiles.
7. Add the favourites picker.
8. Test failure, reconnection and stale-state behaviour.
9. Decide whether the Home Assistant companion still fits comfortably in a package or deserves a custom integration.

## Prior art

Related projects and resources:

- https://github.com/SmartHome-yourself/m5-dial-for-esphome
- https://github.com/samusamu81/M5Dial
- https://github.com/Jasionf/smart-home-button
- https://github.com/Apfelsafft/m5dial
- https://github.com/Skons/M5Dial
- https://esphome.io/components/lvgl/

## Licence

Licensed under the [MIT License](LICENSE).


### Building a page tree

In the visual card editor, expand Home and choose **Add subpage**. Give the new page a title,
select its controls, and add further subpages the same way. IDs are generated automatically.
Drag its handle onto another page's title to nest it, or above/below a title to reorder.
Arrow keys on the handle move it; Left/Right change its nesting. Entity handles reorder controls. Removing a page moves its subpages up one level.
Each page can override the default theme. Existing `lights` lists remain supported; the editor
migrates edited rows to `entities`, which accepts light, switch and cover entities.

Switches toggle on press. Covers show supported Open, Stop and Close touch actions; pressing stops
when supported, and turning sets position only when the cover supports it and reports a position.
Unavailable controls ignore input. Brightness and cover rotation show the requested value locally and send the final target after
150 ms of rotary silence. This uses scene version 2 and requires the matching firmware update. The branded card picker preview stays local.

The advanced Jinja template still overrides page rows and supports HA `custom_templates` macros.
For template leaves, omit profile/style to infer the domain defaults, or use `dimmer` /
`CTL-LIGHT-INSTRUMENT`, `toggle` / `CTL-SWITCH-INSTRUMENT`, or `position` /
`CTL-COVER-INSTRUMENT`. Page themes inherit through the compiled tree.


## Getting started

The firmware and HA custom integration must already be installed. On the first integration
installation, restart HA once so it can load the custom integration. Later integration updates
raise a restart Repair. Each Dial needs a distinct ESPHome device name.

1. **Join Wi-Fi.** On the Dial's Needs Wi-Fi screen, find its setup network, password and
   portal address. Join that network and enter your Wi-Fi credentials in the portal. If the
   portal does not open automatically, use the address displayed on the Dial. The Dial shows
   its selected network while connecting, never the network password.
2. **Add the ESPHome device to HA.** Once Wi-Fi connects, use the displayed IP in HA under
   **Settings → Devices & services → Add integration → ESPHome**. On the same LAN/subnet,
   automatic discovery is expected when mDNS multicast is allowed. Across subnets/VLANs,
   manual addition is normal unless mDNS is forwarded. In the ESPHome device's options,
   enable **Allow the device to perform Home Assistant actions** so it can send input events.
3. **Add HA Dial Server once.** Under **Settings → Devices & services → Add integration**,
   choose **HA Dial Server**. It manages screen definitions, navigation and controls for all
   your Dials. This is separate from adding each physical device through ESPHome. The server
   waits for a card to supply a screen; an API connection alone is not a configured Dial.
4. **Refresh your browser.** Refresh the HA page after adding the server. This made the card
   appear in the verified first-run walkthrough; adding the integration did not require an
   HA restart.
5. **Add the HA Dial card.** Open your dashboard, choose **Edit dashboard → Add card**, search
   for **HA Dial** and choose it. Select your installed Dial from the **Dial device** dropdown;
   **Preview** keeps the simulation local. The list uses compatible ESPHome screen actions,
   excluding unrelated devices. An unavailable saved target remains selected and labelled.
6. **Configure and save.** Expand Home, add a light, switch or cover, and add subpages if
   needed. Save the card and finish editing the dashboard. The saved card sends its screen
   to the Dial; editor drafts stay local. Check the card's deployment status and the physical
   screen, then test one deliberate control action. Use one saved card per Dial to avoid
   different cards sending competing definitions.

The Dial distinguishes Wi-Fi, ESPHome API connectivity and receipt of an HA screen. A waiting
screen with the API connected asks you to add HA Dial Server and then its dashboard card.
Unconfigured Dials do not receive a placeholder menu from a ready event. On connection loss,
the compiled setup interface replaces the cached scene. Touch faults have a separate message.

### Preview size

Set **Preview zoom (%)** in the card editor from 100% to 300% to enlarge the Dial on the
dashboard. The preview fits the available card width; give the card more dashboard columns
when necessary. YAML uses `zoom: 200` for twice the default maximum width. This changes
only the browser preview size; the physical Dial and resolved scene stay at 240 × 240.

### What resets and removals retain

Screen definitions live in HA. Runtime scenes on the Dial are volatile; a device factory reset
cannot erase HA's definitions or the configuration stored in a dashboard card.

| Action | Result |
| --- | --- |
| Ordinary Dial restart or HA restart | Preserves Wi-Fi and saved HA definitions. HA resends the screen after reconnection. |
| Local Wi-Fi reset | Clears the Dial's saved network credentials. HA definitions and dashboard cards remain. |
| ESPHome Factory Reset button | Erases all ESPHome preferences, including provisioned Wi-Fi. HA definitions and dashboard cards remain. |
| Remove a Dial's ESPHome integration entry | Removes its connection from HA. HA Dial Server definitions and cards remain. |
| Remove HA Dial Server | Deletes the server's saved definitions for **all Dials**. Device Wi-Fi and dashboard cards remain. |
| Remove a dashboard card | Removes that card's configuration. The last saved definition remains in HA Dial Server, so the Dial can keep working without an open dashboard. |

**To change one Dial's setup**, edit its card, remove unwanted pages/controls, and save the new
configuration. This replaces its saved definition without affecting other Dials.

With the paired 0.4.0 firmware, server unload also clears the live device screen and shows
setup guidance even if ESPHome stays connected. A later complete scene replaces that guidance.
If the clear cannot be delivered, HA logs the failure; a disconnected Dial uses its local
fallback interface. Older firmware needs the matching update for this explicit clear command.

**To start the server completely fresh**, first remove old cards or change their target to
Preview on every relevant dashboard, then remove HA Dial Server and add it again. A saved
card opened after reinstalling the server can send its configuration again. Leave an old card
in place only if that restoration is intended. Card commands are rejected while the server is
unloaded, so they cannot recreate its deleted definitions before it is re-added.

### Recovery

To change or clear saved Wi-Fi locally, hold the front button for 5–60 seconds and release.
The screen asks **Reset Wi-Fi?** Press briefly to confirm, turn to cancel, or wait 15 seconds.
The hold does not send a control press. Ordinary short presses act on release.

A failed connection reopens the standard ESPHome recovery portal after 30 seconds; driver
failure reasons are shown when available. Wi-Fi and API reboot timeouts are disabled so setup
remains available while HA is unreachable. Reopening the portal and the displayed layout
still require failure-path checks on the physical Dial.

HA's ESPHome device tools expose **Restart**, **Restart in Safe Mode** and **Factory Reset**.
Safe Mode and Factory Reset are disabled by default. Restart preserves settings; Safe Mode
reboots with networking and OTA for recovery. Factory Reset erases the device preferences and
requires Wi-Fi provisioning again. Neither recovery route removes HA dashboard cards.

The HA adapter resends the current scene when ESPHome becomes available. Refreshing a saved
card also resynchronises it without returning Home or changing its saved definition. If the
API is reachable but no screen arrives, check HA Dial Server and the card's deployment status.

A firmware-owned local Settings menu and its availability policy remain planned. The baseline
uses ESPHome's [standard captive portal](https://esphome.io/components/captive_portal/).
Improv Serial/BLE remain alternatives to investigate after the baseline is verified on hardware.

## Versioning

The integration and firmware follow Casa Mia's numbering independently: `YYYY.M.R-bN` for
private builds and `YYYY.M.R` for releases. The month is unpadded, as in HA. Both were migrated
from 0.x to their own `2026.10.1-b1` build on 2026-10-29; matching initial numbers do not couple
future changes.

| Component | Canonical version | Changelog |
| --- | --- | --- |
| HA Dial Server, including its card | `pyproject.toml` | `CHANGELOG.md` |
| Firmware | `firmware/version.yaml` | `firmware/CHANGELOG.md` |

Before editing a component's runtime files, bump that component:

```shell
.venv/bin/python tools/versioning.py bump integration
.venv/bin/python tools/versioning.py bump firmware
```

The command increments the build only if HEAD already contains the current version. Repeated
edits in the same uncommitted build keep its number. Commit the version with the work before
starting the next build cycle. A private build increments bN even if the month changes. After
a release, the next build advances the release number in the same month, or starts the new
month's release 1 at b1. Add that build's notes under the generated changelog heading; breaking
changes come first and explain what the user must do.

The tool stamps the integration manifest from `pyproject.toml`; do not edit the manifest's
version by hand. The card cache key and restart Repair use that installed manifest. Firmware
uses its version substitution for the ESPHome project identity, startup screen and diagnostic
**Firmware Version** text sensor. The sensor publishes once at boot; it does not poll.

```shell
.venv/bin/python tools/versioning.py check integration
.venv/bin/python tools/versioning.py check firmware
.venv/bin/python tools/versioning.py sync integration
```

Compile/deploy tools check the relevant version and metadata before proceeding. Only promote
a release when the owner requests it, using `release integration` or `release firmware` in
place of `bump`. This removes bN, uses the current month if it changed, and combines the build
notes. It does not create a Git tag, publish or deploy anything.

## Atlas editors, appearance and visibility

Each page has **Appearance & conditions**; each entity has **Edit**. The modal is created
only when opened, keeping large navigation trees light. Existing entity strings remain
valid; an edited entity becomes an object with `entity_id` and its overrides.

This build implements two Atlas families: Navigation (**Orbit**, **Pointer**, **Rolodex**, **Petals**, **Constellation**, **Compass**, **Ribbon**, **Breadcrumb**)
and Domain controls (**Instrument**, **Editorial**). The entity selector offers light,
switch, cover, climate, media player, fan, alarm, lock, vacuum, sensor, binary sensor,
weather, timer, calendar, scene, select/input select, number/input number and button/input
button. Sensor presentation variants include energy, air quality, water, vehicle and data.
The watch faces, cameras, ambient screens and historic chart families are not implemented.

Rotary controls use the entity's current limits and step. Media/fan/cover/vacuum actions
respect reported capabilities. Sensors, binary sensors, weather and calendars are read-only;
calendar shows the current event, rather than fetching future agenda entries. Access and alarm
actions require explicit confirmation. PIN-protected actions are unavailable; no PIN is stored.
Draft previews never call entity services. Changing visibility does not provide access control.

The icon picker uses the bundled Material Design Icons font, rendered in HA as a small
mask shared with the card and Dial. It needs no icon download on the device. **Crisp** uses
binary text/digit/icon coverage; **Smooth** uses antialiased coverage. Drawing primitives
keep the shared pixel raster contract. Appearance options are compiled by HA, not browser CSS.

The structured controls and **Advanced style** edit the same settings. Supported declarations:

```css
outer-border: off;
border-width: 2;
accent: #ff8b2d;
background: #060707;
text: #fff7eb;
icon-size: 18px;
font-size: 11px;
orbit-radius: 84px;
raster: smooth;
```

Additional colour keys are `surface`, `secondary`, `quiet` and `grid`. Values must be
`#RRGGBB`. Border width is 1–4, icon size 12–28, title size 6–16 and orbit radius 70–90.
Unknown properties fail validation. Entity overrides can be written directly:

```yaml
pages:
  - id: home
    title: Home
    style: NAV-POINTER
    appearance:
      outer-border: false
      raster: crisp
    entities:
      - entity_id: climate.example
        label: Heating
        icon: mdi:thermometer
        style: CTL-THERMOSTAT-EDITORIAL
        conditions:
          - condition: state
            entity_id: input_boolean.example
            state: "on"
```

Use HA's [condition selector](https://www.home-assistant.io/docs/blueprint/selectors/#condition-selector)
on any page or entity. Supported visibility conditions are `state`, `numeric_state`,
`template`, `and`, `or` and `not`, including nested groups. Conditions are ANDed at the
outer level. HA tracks their state/template dependencies by events, including hidden
branches, and returns to a surviving ancestor if the current page disappears. The root
remains present with an empty list when its conditions fail. Time/device/browser conditions
and state `for` durations are rejected; put those rules in an HA template/helper sensor.

### Optional local settings

The Dial exposes an ESPHome **Show Settings** configuration switch in HA. It defaults off
and restores its last value on reboot. When enabled, **Settings** joins the root menu's
rotary selection and appears as a cog in a reserved inner/top position; it does not reduce the eight normal
orbit destinations. It is absent from sub-pages. Rolodex reserves a top position for it.

The firmware-owned page shows IP, firmware version, uptime, Wi-Fi signal, API/HA status and
touch health. Press or turn to return. With HA unavailable, a short press on the fallback
screen opens Settings when enabled. Turning the switch off closes the page and removes the
cog. The independent physical Wi-Fi recovery gesture is retained even when Settings is off.

Deploy paired firmware before this server build. Scene v3 adds signed/decimal local numeric
feedback; the firmware still accepts v1/v2 scenes. Integration updates require the restart
Repair, then a browser refresh. Dashboard definitions and device Wi-Fi are preserved.
