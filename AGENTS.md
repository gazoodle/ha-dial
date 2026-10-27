Read `AGENTS.core.md` before working in this repository.

# Project instructions

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
