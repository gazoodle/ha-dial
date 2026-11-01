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
  tint and dither for every picture. b28 is the build on HA, copied on 2026-11-01 and its files verified, HA restart pending; firmware unchanged at b5. Panning and
  the panel's column growth have only run against test stubs, so check them in a real browser.
- b23 makes dashboard cards view-and-operate only and adds panel drafts and Operate live house. Two dashboards hold cards
  with stale pages for one Dial: b23 ignores them, but a browser must reload to stop running older card code, and that
  older code is refused by HA. Live operation has only run against fakes.
- b24 reduces the dashboard card's editor to choosing a Dial and removes the card's Preview mode, and b25 adds Follow
  Dial. The card editor, Follow Dial and live switch have only run against test stand-ins, so check them in a real browser.
- b26 splits `__init__.py` and b27 fixes the live banner and reworks door and confirm screens. The
  panel and card have now run in headless Chromium against a stand-in for HA's websocket (scratch only, not in the suite).
- b28 adds white and colour on lights. It has only run against stand-in lights, so check a real
  one: mireds rounding, and lights that report neither temperature nor colour until they're on.
- b21 adds Explorer (`explorer.py`) and b20 the cover safety fixes. Explorer has only
  run against stand-in registries shaped from HA's source, with its HA calls type-checked. First real checks: a live home,
  rebuilds as the registries change and after an HA restart, and the panel's Explorer settings. 
- Until 2026-10-31 the scratch Pyright config checked nothing, because its paths weren't relative, so earlier clean results
  meant little. It now covers the integration with HA's types; the one remaining error is `aiohttp` missing from the venv.
- b19 adds Snake navigation (`snake_path.py`). Its dialog has only run against test stubs;
  check it in the live panel, and turning through a long snake on the Dial. A snake too big for the space shrinks its
  path evenly while its icons keep their size, so sliders near their limits can appear to stop growing it.
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
