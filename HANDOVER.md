# Handover — 2026-10-30

## Admin panel prototype

Integration b7 replaces panel browser confirmations with styled dialogs. Page removal offers
moving direct subpages up while retaining their hierarchy, or removing all descendants; the
count covers every descendant. The local browser mock showed the dialog and editor tests exercised
both choices. b7 was deployed to the HA config share; restart HA and refresh the browser.

Integration b6 adds direct state listeners for visibility, live condition indicators based on
HA template subscriptions, HA state selectors and condition icons, and tabbed appearance/settings
dialogs with sliders, switches and colour swatches. b6 was deployed to the HA config share and
all 39 integration files match; restart HA and refresh the browser. Local tests cover state transitions
and subscription cleanup; the real HA selector and live condition indicators still need checking.
b5 was committed as 939e834. Preserve the separate staged AGENTS.core.md edit.

Integration b5 adds inline visibility rows with an Add condition menu, fixed-time/weekday
visibility scheduled at local-time boundaries, and style/theme galleries rendered by the HA
scene compiler. b5 was deployed to the HA config share; all 39 files match. Restart HA and
refresh the browser. Local browser tests used stub HA forms and gallery responses; real HA
condition selectors and gallery interactions have not been checked. Time helpers as dynamic
boundaries are not supported; fixed HH:MM[:SS] times and weekdays are supported. b5 is
uncommitted. The owner authorised commits needed to continue this panel iteration; preserve
the separate staged AGENTS.core.md edit.

On 2026-10-30 the owner requested Casa Mia's house style and a better editing workflow.
Integration b4 replaces the embedded card-editor presentation with a page tree and focused
inspector, Casa Mia colours/chips/pills, Dial chips and grouped options with a fixed footer.
The original card remains. A local browser mock was checked on desktop and at 390px width;
its HA forms are stubs, so live HA selectors and conditions still need verification. b4 was
copied to the HA config share and all 38 files match; restart HA and refresh the browser to
load it. b4 is not committed; preserve the separate staged AGENTS.core.md edit.

The owner requested a quick multi-Dial panel prototype, keeping the card in place without
spending time on compatibility or migration. The integration registers an admin-only sidebar
panel, loads server definitions, uses the existing editor and isolated card preview, and saves
per Dial. Configuration writes and definition reads require admin. Existing cards can overwrite
panel definitions. The integration b2 build was committed as d35d508, excluding the owner's
staged AGENTS.core.md edit. Integration b3 was copied to the live HA config share and all 37
installed files match source. Restart HA and refresh the browser to activate it; the HA app
showed only its loading screen, so the panel and condition picker have not been checked live.
Panel b3 is committed as 466ad29; firmware remains at b2.

## Overnight commission — implemented and deployed; HA activation pending

The owner approved: domain editors and add-to-tree UI, Crisp/Smooth, Atlas styles (2–3
families acceptable), per-page/entity visibility, icons, compact options dialogs, CSS-like
styling including border toggles, and a root-only settings cog gated by an HA switch.
Deploy changes to HA without waiting for another request. No new commit or push requested.
Preserve separate owner edits in AGENTS.core.md. Previous work is committed as db78e36.
Use tokensave for research, sync after edits, no research agents, updates within 30 seconds.

## Implemented locally in independent integration/firmware 2026.10.1-b2

- catalogue.py owns 21 HA domains and two Atlas families: navigation (all eight Atlas layouts) and domain controls (Instrument, Editorial). Sensor readouts cover Energy,
  Air, Vehicle, Water and Data. Other Atlas families remain outside this batch.
- www/editor/options.js: native modal dialog, HA icon/condition selectors, appearance
  controls and an advanced declaration editor; only mounted when opened. Legacy entity
  strings and rich entity objects both work; move/remove preserves rich settings.
- appearance.py: validated CSS-like declarations, colours, outer border/width, icon/title
  size, orbit radius and Crisp/Smooth. Mask smoothing is shared; primitives retain the
  established raster contract. 7,448 MDI glyphs bundled under resources/ with Apache-2.0 licence.
- visibility.py: HA templates track state, numeric-state, template and AND/OR/NOT
  conditions. Hidden source nodes remain saved. Browser/device/time/duration conditions
  are explicitly rejected; use an HA template sensor for those dependencies. Conditions
  are visibility, not authorisation. Navigator falls back to a surviving ancestor.
- Domain actions live in domain_controls.py; read-only sensor/binary_sensor/weather/
  calendar views, capability-filtered actions, and lock/alarm confirmation. Optional power/cover confirmations preserve the intended action. No PIN storage
  or PIN-protected actions. Drafts simulate actions without services.
- Scene v3 adds twelve-glyph signed/decimal local feedback; v1/v2 remain accepted. Both
  renderers use HA-supplied glyph geometry, precision and gauge ranges. No-feedback uses
  NaN, allowing negative real values. Paired firmware deployment required before new UI.
- ESPHome Show Settings config switch restores persistently, default off. Input and
  acknowledgement metadata report it to HA. Root cog is a ninth selectable item without
  consuming an orbit slot; local diagnostic screen shows IP, version, uptime, RSSI,
  API/HA and touch status. Turning/pressing returns; offline fallback can open it when
  enabled. Disabling closes it. Physical Wi-Fi recovery remains independent.

## Verification and deployment

Both component versions are **2026.10.1-b2**. Paired firmware uploaded to the identity-verified
Wi-Fi Dial; project metadata and the Firmware Version text sensor report b2. Show Settings
exists and reports off by default. The final image includes reset-confirmation precedence and
immediate cached-back dismissal. No factory reset, Wi-Fi reset or consequential entity action
was invoked. Owner-specific source definitions were not edited.

Initial b2 images rolled back to the previous partition. A fresh build alone did not resolve
it. Guarding restored switch callbacks until UI startup, and retaining the original power-hold
setup order, produced a running b2 image verified through native API. Build from the private
fresh build directory for this cycle; do not upload an older binary from another cache.

HA integration, editor modules, fonts and licences were copied to the config share and verified
against source. The share rejected a directory named icons; resources works, and the reader
uses that path. Native HA app window access failed, so **HA restart Repair and browser hard
refresh remain required**. Do not claim the running HA process has loaded b2 or that the live
HA dialog has been checked. Source/node dialog tests and pixel fixtures were checked.

- 64 focused runtime/editor/firmware/version/deployment checks passed in 4.14s on the final
  source. Confirmation markers are scoped to one input, and Ready cannot replay actions.
  All 36 installed component files were verified against source.
- 66 shared fixtures match card and C++ pixels, including all navigation layouts, signed and
  decimal local values, both control treatments and confirmation screens.
- Ruff passes; Pyright uses actual HA 2026.10 types and reports zero errors.
- Preview grid: private /tmp/ha-dial-overnight-preview.png. No new commit/push was requested.
- Remaining owner acceptance: live modal selectors and mobile sizing; physical rotary feel
  for the additional continuous domains; settings on/off, touch/rotary cog selection and
  local back; reset/recovery failure paths. Never call these passed from compilation/tests.


## Prior accepted behaviour / retained gaps

The five-level 5/6/5/6/5 test ended at 5,586 pages (about 406 KB YAML). Physical Dial fast;
editor usable after demand loading, save sluggish, cause unprofiled. Further scale tests
need a credible use case. Whole-tree count/depth/input caps removed; scene bounds retained.
The owner pastes YAML; do not drive the dashboard UI to paste it.

Onboarding/reset documentation and acceptance list are in README.md and BACKLOG.md.
Owner verified factory reset/provisioning, cross-subnet manual ESPHome addition, browser
refresh making the card visible, Dial dropdown, Add subpage and useful waiting screen.
Still needs physical failure-path/reset/recovery checks and measured rotary burst/release.
Removing HA Dial Server clears all server definitions; dashboard cards can intentionally
republish them. Ordinary reload/restart preserves definitions. Firmware only caches current
and previous scenes. Native API connectivity is separate from receiving an HA scene.

Canonical versions: pyproject.toml and firmware/version.yaml. Run versioning.py bump for
runtime edits, one uncommitted build per component, separate changelogs. Compile/deploy check
metadata. No release, tag, commit or push without owner request.
