# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status

The repository contains an end-to-end M5Dial v1.1 prototype:

- `custom_components/ha_dial/`: Home Assistant integration and dashboard card.
- `components/ha_dial/`: reusable ESPHome external component.
- `firmware/`: hardware-only and connected ESPHome configurations.
- `tools/`: direct HA deployment, fake Git hosting, compilation and flashing.
- `tests/`: Python navigation/deployment tests and a host C++ geometry check.

Use `.venv/bin/pytest -q` for the fast suite and
`tools/compile ha-dial-connected.yaml` for the complete firmware build.

## Rules

The owner's shared core rules live in `~/Documents/AGENTS.md` (master). Repos carry a generated copy, `AGENTS.core.md`, loaded via the import below. Never edit `AGENTS.core.md` directly; edit the master and run `~/Documents/sync-agent-rules`.

@AGENTS.core.md

## Code exploration

`.tokensave/` exists and is gitignored. Run `tokensave sync` after source changes and use
the tokensave tools per the core rules.
