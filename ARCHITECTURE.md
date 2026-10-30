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

The editor stores page/entity overrides and a bounded CSS-like declaration vocabulary. HA
validates the options, resolves visibility from state/template events and compiles all layout,
icons and glyphs. Editor dialogs are mounted on demand. Hidden nodes remain in saved source;
removing a current page returns to its nearest surviving ancestor. Conditions are not security
rules. Unsupported condition types fail explicitly. Primitives retain the shared pixel raster;
Crisp/Smooth selects binary or antialiased coverage for HA-generated masks.

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
