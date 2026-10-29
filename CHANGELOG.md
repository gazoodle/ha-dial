# HA Dial Server changelog

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
