Read `AGENTS.core.md` before working in this repository.

# Project instructions

## Configuration panel prototype (2026-10-30)

The owner wants an admin-only multi-Dial integration panel to assess the configuration UX.
Keep the existing card for now; do not spend effort on migration or card compatibility.
Why: the project is not live and the owner wants to evaluate the direction first.

The panel follows the Casa Mia house design language, including its chips, pills and custom
controls. Dialog actions stay visible while their content scrolls. Why: the owner rejected
the prototype's browser controls, cramped card-editor layout and scrolling action buttons.
During this panel iteration the owner authorises the commits needed for subsequent build
cycles; preserve unrelated staged changes. Why: repeated commit questions delayed iteration.

Panel confirmations use the house-styled dialog, not browser prompts. Removing a page offers
keeping its subpages or removing all descendants, with the count. Why: on 2026-10-30 the owner
rejected the browser prompt and wanted an explicit choice about children.

Appearance dialogs keep a stable position between tabs and show a live HA-rendered preview beside
the controls on wide screens. Why: on 2026-10-30 the owner found the moving dialog distracting and
wants to see the effect of the growing set of options while editing.

The panel workspace uses the available browser width, and zooming its preview must not move or
resize the zoom slider or squeeze the page tree. Zoom the Dial inside its scrollable viewport.
Why: on 2026-11-03 the owner found that changing zoom moved the panel out from under the mouse.

A dashboard card only views and operates a Dial. Its settings are which Dial and whether to follow its screen;
it holds no pages, and HA refuses a save that doesn't come from the panel. With Follow off, HA supplies the pages. Why: on 2026-11-01 a card's stale pages replaced a Dial's
saved tree on loading, and the owner ruled that cards can't be editors too.

The panel's Operate live house switch is off whenever the panel opens, and when on the preview says
"Warning: changes made here are live". It's sent with each input, so nothing in HA can stay switched on.

Reset Dial stays available whenever a Dial is chosen; only a reset already running disables it. Why:
on 2026-10-31 the owner found it greyed out after a save and ruled it must be available all the time.

## Crisp is a line-step design (2026-10-31)

Crisp is drawn from simple lines and circles using the line-step algorithms (Bresenham/midpoint),
including its type and icons, and is designed as its own treatment rather than the Smooth layout
redrawn. Never make Crisp by thresholding vector text or icons. Why: on 2026-10-30 the owner ruled
out "just turn off anti-aliasing" because of its pseudo-random pixels; a paraphrase in the handover
lost this and that was built instead. The owner approved the look test on 2026-10-31.

Smooth means real coverage on every primitive, not just text. Why: on 2026-10-31 both modes were
found sharing one aliased primitive raster, with 14% of a thick gauge unpainted.

## Readable on the Dial, but not chunky (2026-11-13)

No default text is under 8 px (`MIN_TEXT` in `canvas.py`) or under 4.5:1 against what it sits on, and
text uses the theme's `label` colour, never `quiet`, which is for lines. A test in
`tests/test_appearance_tokens.py` holds both. Why: the owner found the physical Dial "a little difficult
to see"; 74% of text was 8 px or less on a 0.135 mm pixel, and quiet text was 2.2-3.8:1. The lift was
2 px because the owner asked for "a smidgen bigger without turning into a duplo style interface", and at
3 px labels began to fill their pills. Don't enlarge further without the owner asking.

## The frame decides how big the interior is (2026-11-13)

Layouts draw in design units for the default frame, and `Canvas.scale` grows them about the centre when
the frame gives up room (`_interior_scale` in `scene.py`). So a layout never reads the frame settings
itself, and a setting such as orbit radius means its value at the default frame. Why: the owner asked
that "removing border allows interior to expand"; `outer-border` was read in one place and freed nothing.
It only grows, never shrinks, so text stays readable; type rounds down so it can't outgrow its space; and
picture styles don't scale, because the Dial blits their picture at a fixed size.

## Atlas scope and style settings (2026-10-31)

The Atlas is a starting point, not the target. Editorial is big type, not a thinner Instrument, and
styles must be visibly distinct. Toybox is dropped. Camera and Photo time wait for the image
transport in BACKLOG.md. Why: the owner found the screens samey, and the Atlas's own Editorial
differed only in stroke weight.

A camera is an entity in the tree, with Portal, Cinema and Radar as its styles, not a page style with
a source option. Why: on 2026-10-31 the owner asked why cameras weren't added like every other entity;
there was no good reason. Photos stays a page style, because it is a clock face with a picture behind it.

Every camera and image offers colour, mono, tint and dither, whichever drawing mode is on. Why: on
2026-10-31 the owner pointed out that Crisp and Smooth are about lines and curves, so tying dither to
Crisp, as first built, was wrong.

Snake is the owner's own navigation design: rows read top to bottom in alternating directions, joined
by one line. Twist rotates the whole snake as one, not each row or turn, and icons stay upright. Icons
go per row or along the path, including on the returns. Why: the owner's direction, 2026-10-31.

Explorer is an item, not a Dial mode: it takes one slot on a page, beside the owner's own items and
pages. Why: on 2026-10-31 the owner ruled "it doesn't take over the dial". A generated page of 8 or fewer
items can use any navigation style, and only a longer one is limited to styles that scroll or page. Why:
the owner ruled that styles must not be ignored out of hand. Random is stable per page until Shuffle.
The same limit applies to hand-built pages: over 8 items is allowed in any style that scrolls or pages.
Why: on 2026-10-31 the owner pointed out that some navigators can hold more, and Snake can by scrolling.

Explorer never calls `async_should_expose`, because that saves a default and so changes exposure settings.
Turning the dial never moves a cover that needs confirming, and Stop never waits on a prompt. Why: a
garage door could move on an accidental turn, and stopping one is the safe action.

A door or gate that needs confirming shows its state in words, because it can't be turned; a cover you can
turn keeps its live number. A question replaces the state line rather than sitting beside it. Why: the owner
approved this on 2026-11-01, after the confirm text collided with the state line on every control.

Layouts declare the settings they read in `appearance.py`, and the dialog is generated from that
table. `tests/test_appearance_tokens.py` fails on a declared setting with no effect, on two styles
for a domain that draw the same scene, and on glyph masks in Crisp. Why: 31 of 72 slider positions
on page dialogs did nothing, while all 87 tests passed.

Inspect the rendered result before believing a test. Regenerating fixtures from output locks in
whatever the output is. Why: Crisp cut labels off ("Building" to "Build") and the fixtures locked
that in, visible in the agent's own comparison image.

## Independent versions — Casa Mia rules (2026-10-29)

Firmware and HA Dial Server have separate versions. Before changing runtime code, run
`.venv/bin/python tools/versioning.py bump firmware` or `bump integration`; run both when
both components change. The tool bumps only when HEAD already contains that component's
current version: one build per deployment, not per edit. Commit the version with its changes
before beginning the next build cycle; never commit without the owner's instruction.

Use Casa Mia's `YYYY.M.R-bN` private builds and `YYYY.M.R` releases, with an unpadded month.
A private build increments N even across a month change. After a release, the next build
increments R in the same month, or starts the new month's release 1 at b1. Only the owner
requests/promotes releases; never run `release`, tag or publish one on your own.

The canonical sources are `pyproject.toml` (integration) and `firmware/version.yaml`
(firmware). Never hand-edit the generated integration manifest version or put a firmware
version literal in C++. `sync integration` regenerates the manifest. The firmware substitution
feeds its project metadata, Firmware Version text sensor and compiled startup screen.

Add notes under the component's version heading in `CHANGELOG.md` or `firmware/CHANGELOG.md`.
Breaking changes go first, with the user action required. Build/deploy checks reject an
unbumped runtime change or mismatched metadata. These rules replace the earlier 0.x bumps.
Why: the owner requested Casa Mia's numbering and bump rules with independently identifiable
firmware and integration builds, rather than relying on ESPHome compilation timestamps.

## The Dial owns a value while it's being turned (2026-11-01)

From the first detent the Dial owns the value, and HA can't change the screen until they agree. It sends after
settling, resends if unacknowledged, waits longer if acknowledged but not reached, and after a limit HA wins and
the Dial says so. Why: the owner's design, because a reply to an older value made the screen stutter. Menus stay
HA-drawn for now; the Dial drawing state changes itself is a much bigger piece of work, and in the backlog.

## Verify flash targets (2026-10-29)

Verify the intended device's identity before uploading firmware. Never assume a connected USB
serial device is the Dial; use the confirmed network target for OTA when the Dial is on Wi-Fi.
Why: an agent selected an unrelated USB stick on 2026-10-29 and incorrectly reported a Dial flash.

Read `ARCHITECTURE.md` before changing rendering, navigation, input handling or the HA/card/device
protocol. Its ownership and dependency boundaries are project rules.

## Rotary UX is a release requirement (2026-10-27)

Continuous controls must feel as immediate as the original brightness prototype. Update the local
requested value while turning, coalesce intermediate targets, and send the final target promptly
when rotation stops. Never replay a queue of old brightness or cover commands after release.
Confirmed HA state must not pull an active local adjustment backwards. Cover position uses the
same domain-neutral feedback contract as brightness; domain semantics remain in HA.

Why: the owner found the first scene-based cover control clunky and light updates continuing long
after rotation stopped. That experience is unacceptable as the product UX, even for a first release.
A unit test passing does not establish physical responsiveness: measure burst/release behaviour
and verify it on the Dial before calling this UX complete.

## Simulator controls (2026-10-27)

Use smaller, translucent orange, nearly circular rotation arrows in the card's bottom corners,
mirrored left/right. Keep the CLICK chip over M5, more visible on hover/focus, using Casa Mia's
cm-chip proportions. Why: the owner rejected the separate bottom buttons, top arrows and oversized
chip; the bottom corners are easier to reach with a mouse.

## Home Assistant task ownership (2026-10-27)

HA's async_create_task starts eagerly by default. When a worker removes itself from a task map,
register it with eager_start=False so cleanup cannot run before ownership is recorded. Tests must
exercise HA's eager scheduling, including transport failures before the first yield. Why: an early
scene-send failure left a finished worker cached and silently blocked every later device update.
