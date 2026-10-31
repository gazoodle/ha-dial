# Handover — 2026-10-31

## Current state

Scene v5, the rebuilt Crisp/Smooth, every navigation style, domain graphics and shapes, the settings
table and generated dialog, and the Ambient, Watch and Data faces are implemented and committed in
integration b10 and firmware b4. Decisions and their reasons are in AGENTS.md; the design is in
ARCHITECTURE.md under Scene v5.

Verified: full suite, Pyright with HA 2026.10.4 types, Ruff on the touched files, firmware compile,
browser and C++ pixels identical across all shared fixtures, a 1,368-scene transport sweep, and
inspected contact sheets. The owner reviews sheets by phone; an approved sheet closes that stage.

## Still open

- Deploy: firmware b4 by OTA needs the owner's explicit approval each time, then b10 to HA, an HA
  restart and a browser refresh. Without b4 the Dial rejects every b10 scene and keeps its last one.
- The options dialog and page source fields have only been run against the test harness with stub
  HA forms. Check them in the live panel: group chips, Reset chips, row layout at phone width.
- `history.py` was tested against a fake recorder and its call checked against HA's source, not
  against a live recorder. Check a Data face on real sensors.
- On the Dial: peak heap with v5 scenes, draw time for the 490-segment worst case (NAV-LIST in Crisp),
  rotary feel on faces, and how Crisp's moiré looks on the panel. Only the owner can judge the last two.
- Camera and Photo time wait for the image transport in BACKLOG.md. Toybox is dropped.
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
