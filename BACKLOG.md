# Backlog

## P0 — Make first-run setup self-explanatory

Observed on 2026-10-26: the first physical-device setup required repeated AP checks,
serial monitoring, mDNS inspection and a diagnostic reflash. The device accepted captive-
portal credentials, closed its AP, but neither appeared in Home Assistant nor explained
whether Wi-Fi association had failed. This is too painful for a normal installation.

Design and test an initial UX with explicit states:

1. **Starting** — hardware and firmware identity.
2. **Needs Wi-Fi** — show the fallback SSID, password and portal address on-screen.
3. **Connecting** — show the selected SSID without exposing its password.
4. **Wi-Fi failed** — show a useful reason when available and reopen provisioning.
5. **Connected to Wi-Fi** — show the assigned IP address and that HA discovery is pending.
6. **Waiting for HA** — explain that the ESPHome device must be added separately from the
   HA Dial custom integration.
7. **Ready** — replace setup information with the configured navigation screen.

Acceptance criteria:

- A new device can be installed without opening a serial monitor.
- Failed credentials never leave the device with neither a working station connection nor
  an available recovery AP.
- A documented physical gesture clears saved Wi-Fi and reopens provisioning.
- The screen distinguishes Wi-Fi, API and HA-navigation connectivity.
- HA can be added manually using the on-screen IP when mDNS discovery cannot cross a VLAN.
- Provisioning, incorrect-password, unavailable-network, isolated-VLAN and reboot recovery
  paths are tested on the physical Dial v1.1.
- Touch-controller failure is shown separately and does not obscure network status.

Investigate ESPHome Improv Serial/BLE as a second provisioning route, but keep the captive
portal as the dependency-free baseline unless testing proves it unreliable.

## Camera thumbnail screen

Add a camera view that keeps image processing in Home Assistant. HA should decode, crop and
resize a camera JPEG, convert it to RGB565, and expose the raw frame through a short-lived,
device-scoped local URL. The Dial should stream the bytes into a fixed buffer and keep the
previous complete frame visible until the replacement passes its length and CRC checks.

Start at 128 × 128 (32 KB); test 160 × 160 (50 KB) only if heap measurements remain healthy.
Both sizes fit completely inside the 240-pixel circular display, leaving the outer area for
the orange ring, camera name and navigation. Do not put a general Home Assistant access token
on the device or base64-encode frames into the existing JSON service.

Acceptance criteria:

- Free heap is measured before transfer, during receipt and after releasing the frame.
- Repeated refreshes do not degrade encoder response or API connectivity.
- A failed or partial transfer leaves the previous image visible and reports the failure.
- Frames refresh on screen entry and explicitly configured events, with a conservative timed
  refresh only while the camera screen is visible.

## Additional UX/domain types

- **Alarm panel** — show armed state, available arm modes, entry/exit countdowns and open-zone
  warnings. Support optional on-device PIN entry without retaining or echoing the code, and require
  an explicit confirmation step for consequential actions.
- **QR code** — let Home Assistant generate a scannable code for guest Wi-Fi, onboarding, pairing,
  a dashboard deep link or other configured text. Keep sufficient quiet border and contrast for the
  physical display, and do not expose credentials or long-lived tokens unless explicitly enabled.

## Shared scene model and faithful card preview

Move layout decisions to Home Assistant. HA should resolve each screen into a compact 240 × 240
scene containing final element positions, dimensions, colours, bitmap masks and matching touch
bounds. The device should clip and draw that scene, retain responsive rotary input and optimistic
feedback, and avoid making aesthetic layout decisions such as centring the current pill.

Render the same resolved scene on a canvas in the HA card so it becomes a pixel-accurate live
preview and simulator rather than a stylised approximation. Use the existing transparent dial
branding artwork as the physical surround, with rotate-left, rotate-right and press controls kept
outside the simulated display.

Start with absolute pill placement and the existing compact antialiased mask format. Add good
Casa Mia defaults, then theme-level spacing, colour, scale and typography controls, with explicit
`x`/`y` overrides for users who want them. Cache static scene elements when configuration is saved
and regenerate state-dependent elements only when their content changes.

Acceptance criteria:

- The card and device consume the same resolved scene; there is no duplicate layout logic.
- The card preview matches photographed device output for position, colour and circular clipping.
- Visual bounds and touch bounds cannot drift apart.
- A user can adjust an element's position in HA and see the same result in the preview and device.
- The device retains a useful offline/fallback screen and immediate local rotary feedback.
- Full-frame streaming and a general constraint-layout language remain out of scope until the
  compact scene model proves insufficient.

## Document navigation at large-installation scale

Explain how one Dial can navigate an HA installation with 5,000 or more entities without storing
the entity registry or navigation tree on the device. Use an invented multi-building example with
four or five meaningful levels, such as building → floor → room → function → device, and show that
short lists at each level remain practical with a rotary encoder.

Cover lazy, on-demand navigation generated from HA floors, areas, labels and domains, plus external
building models, templates and hand-authored virtual groups. Document useful refinements including
remembered selection per branch, recent or frequently used items, aggregate room/floor actions,
single-child level skipping, fast-spin acceleration and filtering diagnostic entities from normal
navigation.

Tie the explanation back to the architectural invariant: HA owns the arbitrarily large navigation
graph while the device retains only its current and previous scenes, so installation size does not
determine device memory use.

## Review implementation limits against measurements (2026-10-27)

The current caps are provisional implementation guardrails, not agreed product limits or measured
hardware ceilings: 24 KiB messages, 64 scene elements, 16 touch regions, eight NAV-ORBIT items,
eight tree levels, 64 total tree items/pages and 64 KiB definition input. Review each separately.
Keep the architectural current/previous scene cache and validation at trust boundaries.

- Measure peak free heap and largest allocation during JSON parsing, atomic replacement and mask
  drawing, including old and incoming scenes, plus render and input latency on the actual Dial.
- Derive device budgets from those results. Static build RAM percentages are not peak heap evidence.
- Remove arbitrary whole-tree restrictions; navigation depth and catalogue size belong to HA.
- Treat orbit capacity as a style constraint. Design pagination or other navigation styles before
  allowing extra items to silently disappear.
- Test the full style catalogue on demand; do not preload it into device RAM.

## Next UX pieces (2026-10-27)

- Add per-page Crisp/Smooth rasterisation, with the same resolved output in card and firmware.
- Resolve HA icon overrides and floor/area/domain defaults into compact shared masks.
- Add backend-evaluated page visibility using supported HA conditions, excluding browser/user
  conditions. On removal of the current page, return to its nearest visible ancestor.
- Expose a supported automation/script action for selecting or replacing a definition. Reactive
  Jinja macros already provide dynamic trees; keep stable IDs and preserve valid navigation.
- Implemented 2026-10-27: HA-supplied numeric masks/gauge geometry replace the legacy light
  overlay and provide local cover feedback. Verify burst/release timing on the physical Dial
  after the paired HA/OTA deployment; keep refining until there is no perceptible queued replay.


## Local maintenance and recovery (2026-10-27)

The Dial must explain Wi-Fi, ESPHome API and HA scene readiness separately. A live API socket is
not proof that HA has subscribed or applied the current scene. HA-side availability events and
saved-card mounts now resend the authoritative scene without polling or resetting navigation.

Owner direction: a cog opens firmware-owned Settings, especially from Waiting for HA, and Settings
can remain available throughout normal use. Provide an integration switch to force its availability
on or off; define how that policy is retained while HA is unreachable. A long hold may supplement
the cog, but must not trigger the current control while entering Settings.

- Show on-device diagnostics: Wi-Fi association/address/signal, API connection, HA application
  readiness, firmware version, uptime and the last scene/acknowledgement or failure.
- Offer a QR code to open the appropriate HA/device page, following Casa Mia's approach. Resolve
  the correct local/remote URL through configuration rather than hard-coding a deployment address.
- Allow changing the device name and network configuration locally. Keep stable device identity
  separate from editable display/host names so renaming does not orphan saved cards or definitions.
- Offer retry synchronisation, ordinary restart and OTA recovery using ESPHome's safe mode. Keep
  factory reset separate; ordinary recovery preserves Wi-Fi and saved definitions.
- Add native ESPHome Restart and Safe mode buttons for HA/device tools too.

Existing OTA safe mode handles repeated boot failures; it does not repair a lost HA application
handshake. Agree the Settings flow and force-on/off behaviour before implementing them.

## Stock firmware and first-flash experience (2026-10-27)

Provide a stock firmware image anyone can flash and configure through the Dial's local Settings,
without needing a personal build for a device name or network. Keep the component/package usable
inside an owner's existing ESPHome configuration as an equally supported installation route.

Investigate ESPHome's first-install tooling, including ESP Web Tools or the current ESPHome
browser installer, before building anything custom. Assess supported browsers/platforms, serial
permission and cable guidance, board/image selection, initial Wi-Fi setup, HA discovery, OTA and
recovery. Reuse the standard tools if practical; report the effort and gaps before committing to
an installer project. A polished path from unboxing to the first usable dial is the goal, not merely
a successful flash. Treat this as product UX with clear progress, actionable errors and a way back.

## Touch-controller diagnostics (2026-10-27)

The USB capture during HA reconnect diagnosis included repeated
`ft5x06.touchscreen: Failed to read status` warnings. Investigate I²C/controller behaviour and
physical touch reliability separately from scene delivery; direct native-API scene drawing and
acknowledgement succeeded during the same investigation. Include this fault in the proposed
on-device diagnostics rather than leaving it visible only in a serial log.
