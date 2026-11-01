# Architecture

This document records the rendering and interaction boundaries for HA Dial. They are design
constraints, not implementation suggestions. Change them deliberately and update this document
in the same change.

**Decision — 2026-10-26:** HA owns meaning and layout; the card and device render the same
resolved scene. **Why:** iterating visual details across HA, JavaScript and firmware otherwise
duplicates decisions, mixes concerns and makes the preview disagree with the physical display.

## One authoritative pipeline

```text
saved definition + Home Assistant state
                  │
                  ▼
          Home Assistant scene compiler
                  │
          resolved 240 × 240 scene
             ┌────┴────┐
             ▼         ▼
        card canvas   Dial renderer
```

Home Assistant produces one resolved scene for the current screen. The dashboard card and the
physical Dial consume that scene; neither reconstructs it independently.

## Ownership

### Home Assistant owns meaning

The integration owns configuration, navigation, entity mapping, control profiles, labels, themes
and the current logical screen. It is the only layer that translates an input into a Home
Assistant action or navigation change.

### Home Assistant owns layout

The scene compiler resolves every visual and interactive element to display-pixel coordinates.
It owns positions, dimensions, alignment, circular safe areas, typography, icon placement and
touch bounds. Values derived solely from saved configuration are calculated when that
configuration changes and reused.

The firmware must not centre, distribute or otherwise arrange supplied scene elements. The card
must not recreate those decisions with CSS.

### The device owns hardware

Firmware owns display transport, bounds checking, clipping, primitive drawing, bitmap-mask
composition and physical input sampling. It reports rotary, button and touch input using stable
scene element identifiers or raw coordinates supplied by the hardware.

Firmware also owns a small compiled fallback interface for provisioning, disconnected and fault
states. That interface is not part of the HA scene and must remain usable without HA.

First-run status uses ESP-IDF network events to redraw after ESPHome applies its connection
state; it adds no network polling. Wi-Fi association, API connectivity and a scene received in
the current API connection are separate facts. A cached scene is hidden while disconnected.
The front button sends a short press on release; a five-second hold opens a local Wi-Fi reset
confirmation and never sends the current control action. Reset preserves HA-owned definitions.

### The card owns preview and editing

The card draws the resolved scene on a 240 × 240 canvas. It places that canvas over the existing
transparent Dial artwork and keeps simulator controls outside the simulated display.

Editing changes the saved definition. HA then recompiles and returns the authoritative scene.
The card never treats its DOM or canvas state as configuration.

## Scene contract

A scene is a versioned, disposable description of one complete screen. It uses a top-left origin
and physical display pixels. Every drawable arrives with its final geometry and colour. Visual
elements and their interaction regions share stable identifiers so their bounds cannot drift
apart.

Text and icons that must match between preview and hardware are rendered by HA as compact
antialiased masks or bitmaps. Device fonts are reserved for the compiled fallback interface.

The scene format is independent of its transport encoding. The current JSON service may later be
replaced or supplemented without changing which layer owns layout.

The original scenes use version 1 JSON with a 240 × 240 size, background colour, drawing
elements and touch regions. Elements are circles, straight lines, arcs and pre-rendered text masks.
The masks use packed two-bit coverage; the device expands them directly to pixels. The card uses
the same mask pixels and rasterises the supplied primitive geometry on its canvas. Neither side
chooses scene geometry or font metrics.

Messages carry a strictly increasing revision and are bounded to 24 KiB, including the current
and previous scenes. HA checks the byte limit before sending. The device rejects stale revisions
before replacing either scene and acknowledges an applied revision after drawing it. The card
shows whether it is previewing locally, waiting for the device, awaiting acknowledgement or applied.
Colours are parsed once into compact values on the device. Both renderers use the same integer
raster contract and RGB565 quantisation, checked against shared resolved-scene fixtures.

The card editor stores a repeatable page definition or an optional Jinja template that returns the
page tree. HA validates the result, resolves the current page and compiles its scene; template
definitions are rendered and tracked as their states change. A draft card uses an isolated preview
navigator. A configured card sends its definition when mounted outside the Lovelace editor, so
saving the dashboard deploys the resulting scene to the device.

Drafts have separate preview session identifiers, never write the device's saved definition and
never call entity services. Preview sessions and their template/state subscriptions are removed
when their card disconnects. Cards receive scene changes through a WebSocket subscription;
unrelated Home Assistant state updates do not trigger scene requests.

All incoming scenes are validated before replacing the current scene. An invalid or partial scene
must leave the previous complete scene visible and report the reason.

## Bounded on-demand navigation

Deep navigation lives in HA; the device never receives or stores the navigation tree. HA sends
one complete scene when it is needed, however deep the user travels.

The device keeps exactly two runtime scene slots: **current** and **previous**. When moving
forwards, the validated current scene becomes the previous scene and the newly received scene
becomes current. This gives the device an immediate visual back transition without retaining an
unbounded stack.

On back, the device may display the cached previous scene immediately while sending the back
intent to HA. HA remains authoritative for navigation and supplies the next previous scene on
demand when another level exists. Scene identifiers and revisions must prevent a delayed response
from replacing a newer screen.

The slots are replaced atomically only after a complete scene passes validation. Firmware must
not accumulate older scenes, preload branches of the navigation tree or retain assets that are no
longer referenced by either slot. The compiled offline interface is separate and does not consume
a runtime scene slot.

This bounded two-scene cache is how HA Dial supports a deep, visually rich UX without making its
depth determine device memory use or layout computation.

## State boundaries

Keep these separate:

- **Saved definition:** the user's durable choices and explicit overrides.
- **Runtime state:** navigation, entity values, availability and pending actions.
- **Resolved scene:** disposable output compiled from the first two.

Runtime entity state is never written into saved configuration. Static rendered assets are cached
until their inputs change; state-dependent elements are regenerated only when their content
changes.

## Input path

Card simulation and physical input use the same route:

```text
card or device input
        │
        ▼
navigator / control profile
        │
        ▼
Home Assistant action and updated runtime state
        │
        ▼
new resolved scene
```

There are no card-only navigation shortcuts or domain-specific firmware behaviours.

The device may show immediate optimistic feedback for a latency-sensitive continuous control,
such as brightness. This is an explicit exception: HA remains authoritative, and the optimistic
and confirmed values remain distinguishable until reconciled. Further local behaviour requires a
documented architectural decision.

## Dependency direction

- HA-specific code may depend on the definition, runtime model and scene compiler.
- Transport adapters may depend on the resolved scene, but the scene compiler does not depend on
  a transport.
- The card and firmware depend on the scene contract only.
- The card and firmware never depend on one another.
- Domain controllers do not contain rendering code.
- Renderers do not call Home Assistant services or perform navigation.

## Guardrails

Do not add:

- Position, centring, spacing or typography decisions to firmware.
- A second layout implementation in JavaScript.
- More than the current and previous runtime scene on the device.
- A navigation tree or screen history in firmware.
- Home Assistant entity IDs or service semantics to device rendering code.
- Display concerns to navigation or domain-control code.
- Navigation or domain behaviour to a renderer.
- Transient entity values to persisted configuration.
- Full-frame streaming or a general constraint language until the compact scene model is measured
  and shown to be insufficient.

New scene behaviour needs one small test at its owning boundary. The same resolved-scene fixture
must be usable by the card preview and device-side parser. Geometry changes require a preview
comparison and physical-device verification in proportion to their visual impact.

## Existing migration debt

The prototype predates this contract. Firmware currently calculates positions for rings, menu
items, labels and the name pill. Move those decisions into the HA scene compiler as each area is
next changed; do not extend the old pattern. The existing local brightness feedback and compiled
offline screen are intentional and remain device responsibilities.


## Domain expansion (2026-10-27)

Light, switch and cover state/capability interpretation and service dispatch live in HA.
Switches have no continuous input; covers expose only supported actions and position control.
Their scenes use the existing renderer contract without adding domain behaviour to firmware.
Scene version 2 supplies numeric digit atlases and percentage gauges. Both renderers use HA's
fixed-cell digit masks, colours and gauge geometry; firmware may substitute a local requested
value until HA acknowledges that input sequence. Device fonts are used only in the fallback UI.
The firmware accepts version 1 scenes during upgrades; version 2 requires updated firmware.

Continuous brightness and cover input updates locally and emits a final absolute target after
150 ms of rotary silence. Per-detent callbacks must not redraw synchronously: coalesce a burst
into one deferred display update, including removal of the inherited prototype redraw callback.
The HA publisher keeps one in-flight and one replaceable latest scene, and entity commands are
issued before waiting for display delivery. Acknowledgements include the last device input
sequence, so delayed responses cannot overwrite a newer local adjustment. HA retains the requested
target across intermediate entity reports until confirmation; unavailable controls cancel it.
Physical burst/release responsiveness remains an acceptance check, not a consequence of build RAM
percentages or unit-test success.


## Reconnect and resynchronisation (2026-10-27)

A native API connection can precede HA's event subscription. Treat the device's early `ready`
message as a useful hint, not the sole reconnect mechanism. The HA adapter listens to ESPHome
availability and service-registration events and resends its current scene when the transport
becomes available. A saved-card mount also resends without changing the definition or navigation.
Disconnect events immediately remove the card's applied claim. These are push callbacks, not a
new polling loop. Transport subscriptions belong to the HA integration's unload lifecycle.

## Server lifecycle and saved definitions (2026-10-29)

One HA Dial Server integration manages all Dials. Its internal `ha_dial` domain and the card's
type remain stable. The server persists definitions in HA so a dashboard need not stay open.
An ordinary reload/restart restores them. Removing the server deletes its definitions store;
unloaded server commands reject card requests, and teardown waits for in-flight saves.

The admin-only HA Dial panel edits a selected device's server definition using an isolated
preview session, with a page tree and focused inspector. The existing dashboard card remains independently configured for now and can
still republish its definition. Configuration writes require an administrator.

Panel style and theme galleries use scenes compiled by HA. Fixed-time visibility conditions
schedule local-time boundary and midnight events; they do not poll for state changes.

An admin can reset one Dial's HA configuration. HA stores an unconfigured marker, removes that
Dial's runtime subscriptions, and sends the existing revision-checked clear envelope. The marker
prevents old inputs and legacy defaults from restoring a scene after a restart. Wi-Fi, ESPHome
pairing and firmware are unchanged; an unavailable device clears its cached scene on reconnect.

On unload, the server sends a revision-checked `{"revision": N, "clear": true}` envelope
through the existing view transport. Firmware releases both cached scenes, cancels local
pending feedback and returns to its compiled setup interface while the API can remain
connected. The clear revision is a barrier: older in-flight scenes cannot restore the display.
Clear delivery is bounded and failures are logged; input and scene publishing stop during
unload. This requires the paired 0.4.0 firmware. Acknowledging a clear must not renew the card's
applied-screen claim while the server is offline.

Dashboard cards are separate durable configuration. Removing the server does not delete them;
opening a saved card after reinstalling the server explicitly resends its definition. Removing
a card does not erase the server's last saved definition. Device factory reset affects ESPHome
preferences, not either HA-owned copy. These boundaries must be explained during setup.

A Dial with neither a saved definition nor an explicitly configured fallback remains in the
compiled onboarding interface. Its ready/input events must not create a placeholder screen.

## Appearance, conditional definitions and local settings (2026-10-29)

Chronograph pages resolve HA local time (or an explicit IANA zone), configured world zones,
moon phase and percentage reserve sensors in HA before compilation. One scheduled second-boundary
callback per definition publishes only while a clock is visible. It shares definition subscription
cleanup and the existing coalescing publisher. Resolution occurs once per publication so the
browser and native API delivery use the same reading; previous clock scenes resolve when sent.
No clock, astronomical phase or sensor semantics are added to either consumer. Unknown readings
remain unavailable. A static gallery/appearance preview resolves the instant of its request.

Scene v5 (2026-10-31) is the drawing kit. `polygon` carries 3–128 points in quarter pixels, where a
whole coordinate is a pixel centre, and fills even-odd. `segments` carries up to 256 unconnected
lines as a flat list, so line fans and hatching cost one element. `circle`, `arc` and `gauge` accept
`solid`, a filled band rather than concentric strokes, and arcs accept `cap`. Any primitive with a
`background` blends its coverage against that colour; without one it has hard edges. HA declares the
colour because the Dial has no framebuffer to read back from, and it flattens translucency into
opaque colours. All coverage is integer arithmetic so card and device agree exactly. Pills, thick
lines and hands are polygons built in HA; firmware learns no shape semantics. Masks may reach
240 × 120 and digit cells 64 × 64. HA now emits only version 5, so this needs paired firmware.

`canvas.py` resolves one design vocabulary to scene elements, and layouts draw only through it.
**Crisp** is line-step strokes and hard fills: its text and icons are `segments` from `strokes.py`,
never thresholded glyphs. **Smooth** is coverage on everything, with masks for text and icons. Crisp
is its own design: it has its own default settings and draws tinted surfaces as hatching, so a
layout may branch on `c.crisp`.

Faces (`CHR-`, `AMB-`, `WAT-`, `DAT-`) resolve time, sun, weather and bound metrics in HA at
publication, using the same path as chronographs below. Only chronographs tick each second; other
faces redraw on the minute and on source changes. A source that is missing reads as `--`, and a
metric with no known maximum claims no progress. Data faces read the recorder once per entity and
then append from state events, so a chart adds no polling; history is dropped when a definition is
replaced. Without a recorder a chart says NO HISTORY.

Measured 2026-10-31 across 1,368 scenes (every style, theme and mode, with eight items and long
titles): at most 21,880 bytes for a paired envelope against the 24,576 limit, 38 elements against 64,
and 490 line segments in one scene. Peak heap and draw time on the Dial are not yet measured.

Scene v6 (2026-10-31) adds `image`, for camera and photo faces: a centred rectangle with a size, a
scale of 1 or 2, a CRC, a URL and a placeholder colour. Only scenes with a picture declare version 6.
Pixels never travel in the JSON. HA crops and treats the picture into big-endian RGB565 and serves it
at `/api/ha_dial/frame/<token>`; the unauthenticated token is unguessable, opens one frame and lapses
after five minutes, so the Dial holds no HA credential. The Dial streams into a second fixed buffer on
its own task, so a slow network can't stall rotary input, and swaps only after length and CRC pass; a
failure leaves the old picture up and is reported with free heap on `esphome.ha_dial_frame_status`.
Both 32 KiB buffers are released when no current scene needs them. Browsers get the same bytes as
base64 alongside the scene over the WebSocket. Rounded corners and the picture's treatment (colour, mono, tint
or dither, chosen per picture and independent of Crisp/Smooth) are baked in by HA, so the renderers only blit. The URL must be plain HTTP, because the Dial has no trust store.

Cameras and image entities are tree entities whose styles are `CAM-*`; the watch face `WAT-PHOTOS` is a
page style with a bound image source. Portal's two action entities behave as a small menu inside the
camera's view: pressing one opens that entity's own control, keeping its confirmations and capability
rules, and Back returns to the camera. HA only runs a command if the control pressed is still current
afterwards, so the press that opens a control never operates it.

Capture happens on entering a page and on events from a bound refresh entity or image entity. There is
no timer, so a stale picture shows its age instead. A camera entity's own state is deliberately not a
trigger, because it fires when the access token rotates. No detection boxes are drawn: nothing generic
in HA reports them, and only the bound entity's state and confidence are shown.

Scene v4 adds `polyline`: an ordered list of 2–128 integer pixel-coordinate pairs and a
stroke colour. HA samples curves; both consumers join the resolved points using their shared
Bresenham raster. Coordinates must be within 0–239. Older scene versions cannot carry this
operation. The 64-element and 24 KiB two-scene limits remain unchanged. Eight Petals sectors
need 200 separate segments at twelve samples per curve plus their outer arcs, exceeding the
element limit; paths retain the resolved geometry in eight elements. This requires paired firmware.

The editor stores page/entity overrides and a bounded CSS-like declaration vocabulary. HA
validates the options, resolves visibility from state/template events and compiles all layout,
icons and glyphs. Editor dialogs are mounted on demand. Hidden nodes remain in saved source;
removing a current page returns to its nearest surviving ancestor. Conditions are not security
rules. Unsupported condition types fail explicitly.

Scene v3 extends numeric masks with an explicit twelve-character glyph catalogue, decimal
precision and bounded scaled integer values. HA provides glyph dimensions and gauge ranges;
card and firmware apply the same signed/decimal local value without choosing fonts or layout.
NaN denotes absent local feedback, so negative values are legitimate. Existing v1/v2 scenes
retain their numeric contract and remain accepted by firmware.

Show Settings is an ESPHome config switch, persisted on the device and reported with input
and revision-checked scene acknowledgements. HA adds one root-only selectable cog without
consuming a normal orbit destination. The selected settings view requests the compiled local
diagnostic interface; its geometry and network details belong to the existing firmware-owned
maintenance UI exception. The local policy gates it even if HA sends a settings request.
Disabling closes the page. Recovery input remains independent of this optional menu entry.

## Explorer

A page in a hand-built tree can carry `explorer` options, and `build_definition` then fills it from
`explorer.py`. `read_home` is the only part that touches HA, and it never writes. Generated pages are
ordinary tree nodes with stable ids, so the Navigator, visibility filter and scene code treat them like any
other. The 8-item limit is a property of a style, in `PAGED_STYLES`, not of the tree. Registry events rebuild
the definition after a one-second settle, and `Navigator.restore` returns to the nearest surviving page.

## Cards and the panel

The panel is the only editor. A dashboard card's configuration is a Dial and whether to follow its screen. With
`follow: false`, `ha_dial/browse` gives the card its own Navigator from the Dial's saved pages, whose inputs act on
real devices. By default it shows that Dial's saved pages
through `ha_dial/view`, shares its Navigator, and operates it with `ha_dial/input`. While being added or edited
on a dashboard it shows them on an isolated preview device. The panel's preview is the same element, given a
draft through `setDraft`. `ha_dial/configure` refuses a real Dial without `save: true`, which only the panel
sends. Where this file's earlier sections say a card stores or sends a definition, this section replaces them.
