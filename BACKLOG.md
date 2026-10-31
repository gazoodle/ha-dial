# Backlog

## P0 — Finish and verify onboarding

### Confirmed on hardware / in HA (2026-10-29)

- Factory reset, Wi-Fi provisioning and manual ESPHome addition across subnets were completed
  by the owner. Same-subnet discovery is expected when mDNS is allowed; across subnets manual
  IP entry is normal unless mDNS is forwarded.
- A browser refresh after adding the integration made the card visible; no HA restart was
  needed for that step. Integration code updates still use the existing restart Repair.
- Version 0.3.10's Dial dropdown and Add subpage fix work in the live editor. The physical
  Dial's waiting screen was also confirmed useful.

### Implemented in 0.4.0 — paired deployment completed, HA restart pending

On 2026-10-29, the verified Wi-Fi Dial received the expected firmware build and HA's installed
files/restart marker were verified against source. Complete the restart Repair and browser
refresh before checking the new server behaviour. No real definitions were deleted or
recovery buttons invoked during deployment.

- Rename the shared integration to **HA Dial Server**; retain the **HA Dial** dashboard card.
  One server manages every Dial. Keep internal IDs stable and preserve customised entry titles.
- Show the complete ESPHome → server → browser refresh → card → first control sequence in
  setup and README.md. Remove the optional legacy light field from the initial server form.
- Explain both remaining steps on the API-connected device screen: add HA Dial Server, then
  add the HA Dial card to a dashboard. Do not send a placeholder menu to unconfigured Dials.
- Fix unexpected restoration after server removal. The source was HA's separate definitions
  store: it was reloaded on setup and had no removal hook. Ordinary reloads retain it; removing
  the server deletes it. Unloaded card commands cannot recreate it. Saved dashboard cards are
  independent and can intentionally resend their configuration after the server is re-added.
- Clear the live device screen on server unload even while ESPHome stays connected. A newer
  clear revision prevents delayed older scenes from restoring it; stop input/publication during
  unload and report failed clear delivery. This requires the paired 0.4.0 firmware.
- Document exactly what restart, Wi-Fi reset, factory reset, ESPHome removal, server removal
  and card removal retain. Provide a clear fresh-start procedure and warn that server removal
  clears definitions for all Dials. Do not remove real definitions during deployment.
- Add native ESPHome Restart and Restart in Safe Mode buttons alongside Factory Reset.

### Physical acceptance still open

- Deploy and verify the revised server setup, naming and device wording.
- Repeat server removal/reinstallation with old cards retargeted to Preview: no old definition
  should restore. Then deliberately retarget/open a saved card and verify intentional restoration.
  Back up configurations and agree the reset scope before removing the real server.
- Check incorrect passwords and unavailable networks: the recovery AP must return, its address
  and credentials must remain readable, and no serial monitor should be needed.
- Check the five-second hold, cancellation, confirmation and persistence of the local Wi-Fi
  reset. Entering recovery must never activate the current control.
- Check ordinary reboot/reconnect, native Restart and Safe Mode recovery. Ordinary recovery
  preserves settings. The screen must distinguish Wi-Fi, API and HA scene readiness.
- Check touch reliability/fault reporting separately from network state.
- Measure physical rotary burst/release behaviour for brightness and cover position: immediate
  local feedback, prompt final target and no old queued commands after release. Unit tests alone
  do not close this acceptance check.

Investigate Improv Serial/BLE only after the standard captive-portal baseline is verified.
Local Settings, its cog and force-on/off policy remain a separate design task. Onboarding is
not complete until the whole factory-reset-to-first-control flow works without chat guidance.

## Camera and photo faces: still open

Implemented 2026-10-31 (see ARCHITECTURE.md, Scene v6). Physical checks remain: free heap before,
during and after a transfer (reported in `esphome.ha_dial_frame_status`, logged by HA), that repeated
refreshes don't degrade rotary response or API connectivity, and whether the Dial can reach HA at all
when IoT devices are on another subnet. Consider 160 x 160 frames only if the heap is healthy.

Timed refresh while a camera page is visible needs the owner's approval (core: Push, never poll), so
it isn't built. Detection boxes wait for a concrete source that reports them.

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

Stress testing concluded on 2026-10-29 at five menu levels (branching 5/6/5/6/5),
5,586 pages including Home and approximately 406 KB of YAML. The owner found the physical
Dial fast and the demand-loaded card editor usable; saving was sluggish. The cause of save
latency was not profiled. Further scale testing is deferred until a credible use case needs it.
The arbitrary HA whole-tree count, depth and definition-size caps have been removed.

Remaining device budgets are provisional guardrails, not measured hardware ceilings:
24 KiB messages, 64 scene elements and 16 touch regions. Eight NAV-ORBIT items is a style
constraint. Keep the architectural current/previous scene cache and trust-boundary validation.

- Measure peak free heap and largest allocation during JSON parsing, atomic replacement and mask
  drawing, including old and incoming scenes, plus render and input latency on the actual Dial.
- Derive device budgets from those results. Static build RAM percentages are not peak heap evidence.
- Remove arbitrary whole-tree restrictions; navigation depth and catalogue size belong to HA.
- Treat orbit capacity as a style constraint. Design pagination or other navigation styles before
  allowing extra items to silently disappear.
- Test the full style catalogue on demand; do not preload it into device RAM.

## Next UX pieces (2026-10-27)

- Implemented 2026-10-30: per-page/entity Crisp/Smooth coverage for shared HA-generated text, digits and icons; primitives retain the shared pixel raster.
- Implemented 2026-10-30: MDI selection and entity icon overrides/defaults as shared masks. Automatic floor/area icon defaults remain open.
- Implemented 2026-10-30: per-page/entity state, numeric-state, template and logical visibility,
  with nearest surviving ancestor navigation. Time/device/browser conditions and state durations
  are rejected explicitly; use an HA helper/template sensor. Verify live editor interactions.
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

Implemented 2026-10-30: persisted Show Settings HA switch, root-only rotary-selectable cog,
local IP/version/uptime/RSSI/API/HA/touch diagnostics, offline access when enabled, and local
back behaviour. Both component builds deployed as b2; HA restart Repair/browser refresh and
physical acceptance remain. QR links, local name/network editing and expanded recovery tools
remain open. The physical Wi-Fi reset remains available independently of the cog policy.

Existing OTA safe mode handles repeated boot failures; it does not repair a lost HA application
handshake. The initial diagnostic flow and persisted on/off policy are implemented; validate them physically before extending maintenance actions.

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

## Other ESPHome components on the same device — post-v1 (2026-10-27)

Explore using HA Dial alongside other ESPHome components and attached hardware in the same
device. Check configuration, pin and resource conflicts, and how their entities can appear in
Dial pages through Home Assistant. Preserve the existing ESPHome configuration route.

Consider whether a concrete use case needs the Dial to control local hardware while HA is
unavailable. If so, design ownership and state reconciliation on reconnect before changing the
current HA-owned control architecture.

## Automatic home explorer (2026-10-27)

Offer a card mode that generates Dial navigation from HA floors, areas and entities, so a
usable home can be explored without hand-authoring a page tree. Keep the tree in HA and send
only the current and previous scenes to the device. Adapt the hierarchy to the installation:
start with areas when there are no floors, group large rooms by function, and provide a route to
unassigned entities. Design a rotary list or pagination so the orbit limit never hides items.

Investigate selectable sources: HA's automatic-dashboard visibility and primary entities, the
existing entities exposed to Assist, and an explicitly chosen favourites-only view. Assist
exposure is voice curation, not Dial authorisation; do not change exposure settings. Decide how
hidden entities, diagnostics, configuration entities, unsupported controls and explicit
favourites interact, and explain omissions in the card. Use entity capabilities for controls;
require deliberate interaction for consequential actions.

Explore a per-Dial starting area, favourites, recent items, remembered selection, topic views and
pinning discovered entities to a curated page. Update navigation on HA changes and return to a
surviving ancestor if the current item disappears. Compare the current Apple Watch and Wear OS
companion apps and HA's Home dashboard, and test navigation on the physical Dial at realistic
installation sizes. Expansion of control profiles is a dependency for useful coverage.

Owner's decisions, 2026-10-31 (design agreed, not started):

- Explorer is an item, not a Dial mode. It takes one slot on any page, alongside the owner's own items
  and pages. Why: "it doesn't take over the dial".
- A generated page of 8 or fewer items can use any navigation style. Only a page over 8 is limited to
  styles that scroll or page. Why: the owner ruled that styles must not be ignored out of hand.
- Tree: floors, areas, then function groups for an area over 8; skip empty levels and a lone floor; an
  "Other devices" page for unassigned entities; an entity without an area uses its device's.
- Entities follow HA's automatic dashboard rules, with an optional Assist-only switch and an exclude
  list. The panel explains omissions with counts.
- Locks, alarms and garage, gate and door covers are included and always confirmed; a switch leaves
  them out. Long pages start in List.

Found while planning, and needed before building:

- `async_should_expose` saves a default when an entity has none, so it changes exposure settings. Read
  the saved options directly and never call it.
- Rotating moves a cover even when it requires confirmation, and Stop sits behind the confirm step.
  Close the first and exempt Stop before a garage door can appear. This also affects hand-built pages.
- An entity's unbundled icon looks likely to fail validation of the whole tree (read, not tested).
  Generated items need a fallback icon.
- Many entities have no state when the integration loads at HA start. Build from the registries and
  rebuild once HA has started.

### Needs attention: optional Casa Mia Sensor Watch

Explore a home-screen entry showing non-nominal watched sensors, using the existing Casa Mia
Sensor Watch list service and level-change events rather than duplicating its judgement or
polling. Show severity, value, explanation and age as space permits; support its group filter and
distinguish all clear from unavailable. Consider links to the relevant area or control. Keep Casa
Mia optional and verify the service contract before implementation.
