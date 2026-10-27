# M5Dial Controller for Home Assistant

A beautiful, dynamically assigned physical control surface for Home Assistant.

Home Assistant chooses what the Dial controls. The Dial chooses the right interaction and presentation for it.

Turn it. Press it. Done.

> Status: end-to-end light dimmer prototype and hardware bring-up

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

- A multi-page Home Assistant dashboard.
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
Home Assistant card
└── Dial-shaped editor, preview and test controls
          │
Home Assistant integration
├── navigation tree and current-screen resolution
├── target and state updates
└── execution of semantic commands
          │
          │ ESPHome native API
          ▼
Reusable ESPHome component
├── hardware support
├── current-screen state only
├── control profiles
├── round-display presentation
└── encoder, button and touch input
```

The integration owns the complete navigation tree. The device asks Home Assistant to move between screens and retains only the current compact view, while rotation feedback remains local. The card and physical Dial drive the same navigation model.

Other Home Assistant tools may use the public protocol in the future, but the project does not depend on them.

## Protocol model

Home Assistant sends a target descriptor containing only what the Dial needs:

```json
{
  "entity_id": "climate.example_thermostat",
  "name": "Example thermostat",
  "profile": "thermostat",
  "state": "heat",
  "value": 20.5,
  "minimum": 7,
  "maximum": 30,
  "step": 0.5,
  "unit": "°C",
  "available": true
}
```

The Dial returns semantic commands:

```json
{
  "entity_id": "climate.example_thermostat",
  "command": "set",
  "value": 21.0
}
```

Home Assistant remains responsible for translating commands into domain actions and checking the current capabilities of the entity.

The exact transport and message schema are not stable until the hardware prototype proves them.

## Target for the first usable release

The first usable release supports:

- M5Stack Dial v1.1.
- Wi-Fi provisioning.
- Encrypted ESPHome API.
- OTA updates.
- Rotary encoder, push button, touch, display and backlight.
- Idle, focused, picker, unavailable and disconnected states.
- `dimmer`.
- `thermostat`.
- `volume`.
- `selector`.
- Runtime target changes without reflashing.
- Optimistic local feedback followed by HA state reconciliation.
- An LVGL desktop simulator or equivalent fast UI preview.

It does not initially include colour selection, covers, album art, NFC, alarms, themes or a general plugin system.

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

On the first deployment, restart Home Assistant manually and then add the HA Dial integration under **Settings → Devices & services**. Choose the light during setup, or use **Configure** on the existing HA Dial integration. The card is registered automatically; add this manual card to a dashboard:

```yaml
type: custom:ha-dial-card
device: ha_dial
```

The underscore is the ESPHome service slug; the firmware node name remains `ha-dial`.
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
      url: git://192.0.2.10:9419/ha-dial
      ref: fake-git-host
    components: [ha_dial]
```

For a browser-only preview of the orange-ring Dial and its rotate, press and touch interactions, run `python3 -m http.server` in the repository and open `http://localhost:8000/tools/card-preview.html`.

After checking the detected serial port, flash it explicitly:

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
