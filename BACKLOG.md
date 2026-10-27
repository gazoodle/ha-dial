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
