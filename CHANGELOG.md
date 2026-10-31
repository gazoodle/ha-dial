# HA Dial Server changelog

## 2026.10.1-b16

- Fix setting groups running off the edge of the Options dialog on a phone, and list a style's own settings first.

## 2026.10.1-b15

- Add a Colour switch to the Portal and Radar camera styles.

## 2026.10.1-b14

- Fix camera gallery thumbnails all showing the selected style's picture.

## 2026.10.1-b13

- Add a Zoom slider to the preview, enlarging the whole rectangle up to 400% with panning where it no longer fits. Each browser remembers its own zoom. This replaces the card editor's Preview zoom setting, and a saved `zoom` value is ignored.

## 2026.10.1-b12

- **Breaking: a page saved with a camera style no longer loads.** Add the camera to the page as an entity instead; there is no migration.
- Cameras and image entities are now added to the tree like any other entity, with Portal, Cinema and Radar as their styles.
- Portal's two action buttons are entities you bind, and each opens that entity's own control, with Back returning to the camera. Opening a control never operates it.

## 2026.10.1-b11

- **Requires firmware 2026.10.1-b5 for pictures.** Pages without a picture still work on b4.
- Add Camera faces (Portal, Cinema, Radar) and watch Photos, from camera or image entities, captured on page entry and on bound entity events. A capture failure keeps the last picture and says so.
- The Dial must reach HA's internal URL over plain HTTP. Frames are served at an unauthenticated, expiring, single-frame URL.

## 2026.10.1-b10

- **Breaking: requires firmware 2026.10.1-b4.** HA now emits scene version 5, which older firmware rejects while keeping its last screen. Upload the firmware, then restart HA and refresh the browser.
- Rebuild Crisp as true line-step drawing, with single-stroke type and line icons, and Smooth as real anti-aliasing on every shape. Crisp no longer cuts labels off.
- Redraw all navigation styles and add List, Grid, Pager and Needle.
- Give each domain its own graphic, replace Editorial with big type, and add Column, Segment and Tumbler. Action buttons use icons, so their labels can't overflow.
- Add Ambient, Watch and Data faces with real sun, weather, metric and recorder sources. Toybox is dropped; Camera and Photo time wait for an image transport.
- Add about 50 style settings covering padding, sizes, gaps, widths, borders and positions. The dialog shows only what the current style reads and saves only what you change.
- Faces other than chronographs now update once a minute, not every second.

## 2026.10.1-b9

- Add all four Atlas chronographs: Tricompax, Worldtimer, Skeleton and Moonphase, with real time, IANA zones, optional HA moon and reserve sensors, and scheduled updates with subscription cleanup.
- Add clock settings and HA-rendered gallery previews; retain the same resolved browser/device scene.

- Introduce scene v4 polylines for HA-resolved curved Petals outlines without exceeding the element budget; requires paired firmware.
- Draw navigation ornaments behind the centre, contain Petals labels and move its settings cog clear of the destination icons.

## 2026.10.1-b8

- Add centre radius and gauge radius and width controls to the appearance dialog.
- Draw crisp text, digits and icons directly at display resolution instead of thresholding smoothed masks.
- Restore distinct petal and pointer navigation details and add a highlight radius control.
- Keep the appearance dialog stable between tabs and show an HA-rendered live preview beside its controls.
- Add a confirmed per-Dial configuration reset that removes saved pages and clears the device display without changing Wi-Fi or firmware.

## 2026.10.1-b7

- Replace browser confirmations with styled dialogs; choose whether to keep or remove nested subpages when removing a page.

## 2026.10.1-b6

- Watch visibility condition entities directly and show live condition results using Home Assistant template subscriptions.
- Use Home Assistant state selectors and condition icons, with tabbed dialogs, sliders, switches and colour controls.

## 2026.10.1-b5

- Add server-rendered Atlas style and theme galleries and inline visibility condition editing.
- Support fixed time and weekday visibility conditions, with scheduled updates at time boundaries.

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
