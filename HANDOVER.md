# Handover — 2026-10-31

## Current state

Scene v5, the rebuilt Crisp/Smooth, every navigation style, domain graphics and shapes, the settings
table and generated dialog, and the Ambient, Watch and Data faces are implemented and committed in
integration b10 and firmware b4, with pictures added in b11 and b5. Decisions and their reasons are in AGENTS.md; the design is in
ARCHITECTURE.md under Scene v5.

Verified: full suite, Pyright with HA 2026.10.4 types, Ruff on the touched files, firmware compile,
browser and C++ pixels identical across all shared fixtures, a 1,368-scene transport sweep, and
inspected contact sheets. The owner reviews sheets by phone; an approved sheet closes that stage.

## Still open

- Activate: on 2026-10-31, with the owner's approval, firmware b4 went on by OTA (identity checked,
  native API reports b4) and b10 was copied to the HA config share (all 47 files match). HA still
  needs a restart and the browser a refresh. No v5 scene has reached the real Dial yet, so the first
  one after the restart is the first hardware test of the new renderer.
- The options dialog and page source fields have only been run against the test harness with stub
  HA forms. Check them in the live panel: group chips, Reset chips, row layout at phone width.
- `history.py` was tested against a fake recorder and its call checked against HA's source, not
  against a live recorder. Check a Data face on real sensors.
- On the Dial: peak heap with v5 scenes, draw time for the 490-segment worst case (NAV-LIST in Crisp),
  rotary feel on faces, and how Crisp's moiré looks on the panel. Only the owner can judge the last two.
- Cameras became tree entities in integration b12, b13 added the preview zoom slider, and b17 added colour, mono,
  tint and dither for every picture. b16 is the build on HA, copied on 2026-10-31 and its files verified, HA restart pending; firmware unchanged at b5. Panning and
  the panel's column growth have only run against test stubs, so check them in a real browser.
- Camera and Photo faces and the frame transport are implemented in integration b11 and firmware b5,
  deployed 2026-10-31 with approval (b5 reported by the Dial, b11 files verified) but not activated:
  HA needs a restart. Tested against fakes only. First real checks: a live camera entity,
  whether the Dial can reach HA across subnets, and the heap figures HA logs from each fetch. Open
  items are in BACKLOG.md. Toybox is dropped.
- Crisp's stroke font folds to unaccented capitals and shows a box for anything else, so a non-Latin
  label is unreadable in Crisp. Decide whether that matters before any release.
- `tests/fixtures/scenes.json` is now about 1.5 MB. The suite still runs in about 11 seconds.

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
