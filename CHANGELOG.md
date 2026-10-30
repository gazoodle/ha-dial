# HA Dial Server changelog

## 2026.10.1-b4

- Give the configuration panel Casa Mia styling, a page tree and focused inspector, and keep dialog actions visible while scrolling.

## 2026.10.1-b3

- Add an admin-only configuration panel with per-Dial drafts and an interactive preview.

## 2026.10.1-b2

- Requires paired b2 firmware for signed/decimal local feedback and the gated local settings page; restart HA after deployment and refresh the browser.
- Add modal page/entity editors, 21 HA domains, two Atlas families with all eight navigation layouts and Instrument/Editorial presentations, and read-only sensor variants.
- Add MDI icons, Crisp/Smooth masks, border/colour/size controls and validated CSS-like declarations.
- Add event-driven state/numeric/template/logical visibility with nearest surviving ancestor navigation.
- Add explicit lock/alarm confirmations and keep PIN-protected actions unavailable; drafts remain isolated.
- Add a root-only, selectable settings cog gated by the persisted ESPHome Show Settings switch.

## 2026.10.1-b1

- Rename the shared integration HA Dial Server and explain first-run setup and recovery.
- Remove saved server definitions on integration removal, retain ordinary reloads, and clear live screens on unload with paired firmware.
- Offer installed Dials and Preview in the editor; fix Add subpage on ordinary HTTP.

- Add a dashboard preview zoom setting from 100% to 300%, constrained to the available width.

- Demand-load editor controls and child headings when pages expand; release collapsed branches, retain edits and expansion state, and index children once per tree rebuild.
- Remove HA-wide page/item count, depth and definition-size caps; retain device scene bounds.
- Adopt Casa Mia's calendar version and build numbering, independently of the firmware.
- Use the manifest version for the dashboard card's cache key.

Previous development builds used 0.x versions; the last paired update was 0.4.0.
