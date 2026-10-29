# Handover

Latest update, 2026-10-29: added a presentation-only preview zoom slider (100–300%) and
`zoom` YAML option, fitting the available dashboard width. The device scene is unchanged.
Full suite: 55 tests passed in 4.01s, including Node editor/card checks and C++ boundary checks.
Updated the obsolete depth-cap test to assert that nine levels are accepted. Zoom deployment
is included in the current HA copy; browser hard refresh is required. No live zoom visual check.

Latest UX-test change, 2026-10-29: the owner confirmed the 1,086-page, four-level tree is
fast on the physical Dial but extremely slow in the HA editor. The editor eagerly mounted
2,172 page forms, including entity selectors in collapsed branches. Implemented local
on-demand controls/child headings using native details toggle events; collapsing removes
content, retaining saved configuration and expansion state. Children are indexed once per
rebuild; unchanged page references avoid serialising the tree on unrelated HA updates.
The focused Node card checks pass, including 1,086 pages mounting only two initial page
forms, collapse/reopen with edited titles, retained expansion, no updates to detached forms,
and existing add/remove/reorder behaviour. Deployed to the HA config share and editor contents verified against source.
Browser hard refresh still required; no live browser timing yet.
Integration remains 2026.10.1-b1 under the same-uncommitted-build version rule.

Owner instruction, 2026-10-29: deploy code changes to HA after each turn during this rapid
iteration, without waiting for another deployment request. Continue to report any required
HA reload/restart and browser refresh. Generated a five-level stress tree in private temporary
storage using branching 5/6/5/6/5: 5,586 pages including Home. The owner pastes YAML.
Do not drive the dashboard UI to paste it. The owner has now ended scale testing: the
five-level card is usable after demand loading, save is sluggish, and the device remains fast.
Further scale work needs a credible use case; save latency was not profiled.

Earlier in this UX test, removed HA-side 64-page, 64-total-item, eight-level depth and 64 KiB
input caps at the owner's request, without tests as requested then. That integration was
copied to HA. Per-page orbit capacity, validation and device scene bounds remain.

## Independent calendar versions — 2026-10-29

Integration metadata deployed with the limit removal; calendar-version firmware has not
yet been deployed. The owner's requested Casa Mia rules were read from
its CLAUDE.md (Rule Zero and Version) and tools/versioning.py. Firmware and integration each
start independently at **2026.10.1-b1**. Future versions follow `YYYY.M.R-bN` private builds /
`YYYY.M.R` releases, month unpadded. Private builds increment bN across month changes; after a
release, advance R in the same month or start the new month's release 1 at b1. Only promote
or publish a release on the owner's explicit request.

Use `.venv/bin/python tools/versioning.py bump firmware` or `bump integration` before runtime
edits. The command bumps only if HEAD already contains that component's current version;
multiple edits within the same uncommitted build do not consume build numbers. Commit the
version with the changes before the next build cycle, only when the owner asks to commit.
Sources: pyproject.toml for HA Dial Server, firmware/version.yaml for firmware. Separate
changelogs are CHANGELOG.md and firmware/CHANGELOG.md. The tool stamps the integration
manifest; the card now uses that manifest version without a duplicate const.py literal.
Compile/deploy commands check the relevant version, changelog and metadata.

ESPHome's base package publishes a diagnostic **Firmware Version** template text sensor once
at boot, with update_interval never. Its value, native project metadata and startup display
all use the firmware version substitution. Connected firmware compiled successfully; generated
code was checked for matching project/sensor values and disabled polling. Live sensor
verification requires the next authorised OTA. No tag, commit, release or deployment was made
as part of this versioning change.

Verification for this change: 41 focused versioning, lifecycle, transport, card, deployment
and firmware tests passed. Ruff and Pyright passed with zero errors for the changed Python
files. The connected firmware build succeeded; both component version checks pass.

## Onboarding candidate 0.4.0 — 2026-10-29

Paired deployment authorised and completed on 2026-10-29. The identity-verified Wi-Fi Dial
accepted OTA and reports the expected new build, plus Restart,
Restart in Safe Mode and Factory Reset. Safe Mode and Factory Reset are disabled by default;
none of the recovery buttons was invoked. HA Dial Server 0.4.0 was copied to the config share;
all installed files and the restart marker match source. The HA restart Repair and browser
refresh still need completing before claiming that HA is running the new server code.

### Implemented

- The shared integration is named **HA Dial Server**, installed once for all Dials. The
  dashboard card remains **HA Dial**. Internal IDs are unchanged; the old default entry title
  migrates while customised titles are preserved.
- Initial server setup explains ESPHome, permission for HA actions, browser refresh, adding
  the card, selecting the Dial and saving. The legacy fallback light is available in options
  rather than the initial form. README.md contains the complete sequence and reset table.
- Unexpected old screens came from HA's separate definitions store, loaded on every setup
  without a removal hook. Ordinary reloads preserve it; removing the server now deletes it
  for all Dials. Commands reject requests while unloaded, and teardown/removal synchronise
  with saves so old open cards cannot recreate deleted storage while the server is absent.
- Dashboard cards are independent configuration: reopening one after reinstalling the server
  can intentionally resend it. For a fresh start, remove or retarget old cards to Preview
  first. Removing a card alone preserves the last server definition for dashboard-free use.
- An unconfigured Dial's ready/input events no longer trigger a placeholder menu. It remains
  on onboarding until a card supplies a definition (or an explicit legacy fallback is set).
- Firmware says "Add HA Dial Server / then add HA Dial card / to a dashboard". Native Restart
  and Restart in Safe Mode buttons accompany Factory Reset; the latter two are disabled by
  default. No device reset or real definition deletion was performed during this work.
- Server unload explicitly clears live screens through a newer-revision clear envelope,
  preventing cached scenes from looking live while ESPHome remains connected. Firmware drops
  both cache slots and pending local feedback; stale scene/clear messages are rejected. Card
  subscribers receive an offline message, and clear acknowledgements do not restore an applied
  claim. Clear delivery is bounded and failures are logged. Deploy paired firmware first.

### Verification

- 22 focused lifecycle, integration, transport, card, deployment and firmware tests passed.
  Lifecycle tests cover reload/restore, removal/re-add, rejected unloaded commands, concurrent
  saves/removal, custom names and withholding placeholder screens from unconfigured devices.
  Tests also cover clear delivery, stale/malformed clear requests, late input/publication after
  unload, and clear failures preserving saved configuration while reporting the reason.
- Connected firmware compiled successfully. Ruff passed; Pyright reported zero errors for
  changed Python files using HA 2026.10's actual package for types, downloaded only into a
  temporary folder. No new project dependency was installed. Full suite was not run.
- Previously confirmed by the owner: factory reset and Wi-Fi reprovisioning, manual ESPHome
  addition across subnets, browser refresh making the card visible, the device dropdown,
  Add subpage over HTTP and a useful physical waiting screen.

### Next

Use the restart Repair and refresh the browser. The remaining physical acceptance list
is under P0 in BACKLOG.md: revised setup/naming, clean removal and intentional card restore,
wrong/missing Wi-Fi, local reset gesture, ordinary restart/Safe Mode, touch faults and measured
brightness/cover burst-release responsiveness. Agree scope/backups before destructive tests;
removing the server affects all Dials. Local Settings/cog policy remains a separate design task.

### Flash-target correction

On 2026-10-29 an unrelated USB stick was incorrectly selected and a Dial flash claimed;
the owner reports it did not flash. The real Dial is on Wi-Fi. Follow AGENTS.md's identity
check rule before any upload; never infer the target from a connected serial port alone.
