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
