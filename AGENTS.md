Read `AGENTS.core.md` before working in this repository.

# Project instructions

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
