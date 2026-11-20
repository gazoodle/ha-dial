# HA Dial Server changelog

## 2026.11.1

- Install from the Marketplace (HACS): the repository now has the files and checks it needs. Home Assistant 2026.10 or later is required.
- No firmware change is needed, but firmware 2026.10.1-b7 corrects the setup screen's advice.

- Make small text easier to read on the Dial. Labels, captions, units, details and Back and Home are 2 px larger by default, and text is no longer shrunk below 8 px to fit: it's shortened with two dots instead. A page that saved its own label, detail or unit size keeps it.
- Draw dim captions in a brighter colour. They used the quiet colour, which is meant for lines and was too faint for text in every theme. Setting a quiet colour no longer changes caption text; the secondary colour does.
- Re-fit the screens the larger text crowded: the World Timer's zones, the Radar and Status faces, the Modular face's time, and the Tumbler's detail line.
- Hiding the outer ring, or slimming it, now lets the screen grow into the room: everything is drawn up to 7% larger about the centre. Before, only the ring went and the space stayed empty. Camera and photo screens don't grow, because their picture is a fixed size. A heavier frame doesn't shrink anything.
- No firmware change is needed.

- Keep each Data face's requested history range separate, including when sensor events update the charts.
- Capture a camera freshly on entry even when another camera's capture is still running.
- Use the full browser width for the panel and keep its preview slider and editor columns steady while zooming.

- Fix pale colours when turning a light that was in white. Colour now starts at full saturation unless the light is already in colour.
- A light's rounding no longer stops a colour or white value counting as reached, including around 359° to 0°, and a control shows what was asked for once it's close.
- Asking for a value a control already holds no longer leaves it pending. The Dial's new firmware relies on this.
- HA logs a warning when a Dial gives up on a value.

- Lights that support them now offer tunable white and colour. A button on the control moves turning between brightness, white and colour, offering only what the light can do. The ring shows the real range in colour, in every light style. No firmware change is needed.

- Fix the Operate live house warning never appearing: each redraw of the preview blanked and hid it.
- The help line under Try your Dial now wraps instead of widening the panel.
- Doors, gates and other covers that need confirming now say their state in words, such as CLOSED or OPENING 40%, and ask in a large line, such as OPEN THE DOOR?. Covers you can turn keep their live number, in a clear band in the graphic.
- On every control, the confirm question replaces the state line instead of overlapping it, and action buttons no longer share a touch area with Back and Home.

- Internal: the websocket commands moved out of the integration's main file into `commands/`. No change in behaviour.

- New card setting, Follow the Dial's screen, on by default. Off, the card browses on its own, so using a dashboard doesn't disturb the Dial on the wall. It still operates real devices, and it follows saved changes to the Dial's pages.

- A dashboard card's only setting is now which Dial it shows. Its pages, theme, template and Preview options are gone, and saving a card clears any it still held. All editing is in the panel.
- A dashboard card keeps its zoom slider, starts at 100%, and remembers its size per Dial in that browser, separately from the panel's preview. A new card starts on your first Dial.

- A dashboard card can no longer replace a Dial's saved pages. A card set to a real Dial used to send its own copy of the pages whenever it loaded, which overwrote the Dial's tree. It now shows the pages saved on that Dial, and HA refuses a save that doesn't come from the panel.
- Unsaved work in the panel survives leaving the page: it's kept in your browser and restored when you return, with a Discard changes button.
- A dashboard card starts at 100% zoom. Only the panel's preview remembers its size.
- New Operate live house switch beside Save and Reset, off whenever the panel opens. While it's on, the preview's controls operate real devices and the preview shows a warning. Page edits still wait for Save.

- A hand-built page can now go past 8 items in a style that scrolls or pages: List, Grid, Snake, Compass, Ribbon, Rolodex or Pager. Its style gallery offers only those while it holds more than 8.
- Explorer now offers a camera style and picture treatment for its cameras and images.

- New Explorer: an item you add to any page, beside your own items and pages, that fills itself from your floors, areas and entities. It can cover the whole home, one floor or one area. Pages of up to 8 items can use any navigation style; longer ones use a style that scrolls or pages. Each page can have its own look, or Random shows off every style. The panel lists what was left out and why, and locks, alarms and doors always ask for confirmation.
- The Pager style's dots no longer overflow on a long page.

- Turning the dial no longer moves a cover that needs confirming; opening and closing still ask. Stop on a cover now acts at once, so stopping a moving door never waits on a prompt.
- An entity whose icon isn't in the bundled set now falls back to its domain's icon. Before, one such icon made the whole page tree fail to save.
- When the page tree is rebuilt, the selection stays on the same item, and having Device settings open no longer causes an error.

- New Snake navigation: icons in rows joined by U-turns, read in snake order. Choose icons per row or along the path, including on the returns, with controls for turn extension, whole-snake twist, row length, turn radius, position, single or double edges, width, gap, clearance and colours. Past what fits, it scrolls a row at a time.

- Reset Dial is always available once a Dial is chosen. A finished save used to leave it greyed out until the next edit, and a save in progress blocked it.

- Every camera and image now offers colour, mono, tint and dither, in either drawing mode. This replaces the Colour switch, and Crisp no longer forces a dither.

- Fix setting groups running off the edge of the Options dialog on a phone, and list a style's own settings first.

- Add a Colour switch to the Portal and Radar camera styles.

- Fix camera gallery thumbnails all showing the selected style's picture.

- Add a Zoom slider to the preview, enlarging the whole rectangle up to 400% with panning where it no longer fits. Each browser remembers its own zoom. This replaces the card editor's Preview zoom setting, and a saved `zoom` value is ignored.

- **Breaking: a page saved with a camera style no longer loads.** Add the camera to the page as an entity instead; there is no migration.
- Cameras and image entities are now added to the tree like any other entity, with Portal, Cinema and Radar as their styles.
- Portal's two action buttons are entities you bind, and each opens that entity's own control, with Back returning to the camera. Opening a control never operates it.

- **Requires firmware 2026.10.1-b5 for pictures.** Pages without a picture still work on b4.
- Add Camera faces (Portal, Cinema, Radar) and watch Photos, from camera or image entities, captured on page entry and on bound entity events. A capture failure keeps the last picture and says so.
- The Dial must reach HA's internal URL over plain HTTP. Frames are served at an unauthenticated, expiring, single-frame URL.

- **Breaking: requires firmware 2026.10.1-b4.** HA now emits scene version 5, which older firmware rejects while keeping its last screen. Upload the firmware, then restart HA and refresh the browser.
- Rebuild Crisp as true line-step drawing, with single-stroke type and line icons, and Smooth as real anti-aliasing on every shape. Crisp no longer cuts labels off.
- Redraw all navigation styles and add List, Grid, Pager and Needle.
- Give each domain its own graphic, replace Editorial with big type, and add Column, Segment and Tumbler. Action buttons use icons, so their labels can't overflow.
- Add Ambient, Watch and Data faces with real sun, weather, metric and recorder sources. Toybox is dropped; Camera and Photo time wait for an image transport.
- Add about 50 style settings covering padding, sizes, gaps, widths, borders and positions. The dialog shows only what the current style reads and saves only what you change.
- Faces other than chronographs now update once a minute, not every second.

- Add all four Atlas chronographs: Tricompax, Worldtimer, Skeleton and Moonphase, with real time, IANA zones, optional HA moon and reserve sensors, and scheduled updates with subscription cleanup.
- Add clock settings and HA-rendered gallery previews; retain the same resolved browser/device scene.

- Introduce scene v4 polylines for HA-resolved curved Petals outlines without exceeding the element budget; requires paired firmware.
- Draw navigation ornaments behind the centre, contain Petals labels and move its settings cog clear of the destination icons.

- Add centre radius and gauge radius and width controls to the appearance dialog.
- Draw crisp text, digits and icons directly at display resolution instead of thresholding smoothed masks.
- Restore distinct petal and pointer navigation details and add a highlight radius control.
- Keep the appearance dialog stable between tabs and show an HA-rendered live preview beside its controls.
- Add a confirmed per-Dial configuration reset that removes saved pages and clears the device display without changing Wi-Fi or firmware.

- Replace browser confirmations with styled dialogs; choose whether to keep or remove nested subpages when removing a page.

- Watch visibility condition entities directly and show live condition results using Home Assistant template subscriptions.
- Use Home Assistant state selectors and condition icons, with tabbed dialogs, sliders, switches and colour controls.

- Add server-rendered Atlas style and theme galleries and inline visibility condition editing.
- Support fixed time and weekday visibility conditions, with scheduled updates at time boundaries.

- Give the configuration panel Casa Mia styling, a page tree and focused inspector, and keep dialog actions visible while scrolling.

- Add an admin-only configuration panel with per-Dial drafts and an interactive preview.

- Requires paired b2 firmware for signed/decimal local feedback and the gated local settings page; restart HA after deployment and refresh the browser.
- Add modal page/entity editors, 21 HA domains, two Atlas families with all eight navigation layouts and Instrument/Editorial presentations, and read-only sensor variants.
- Add MDI icons, Crisp/Smooth masks, border/colour/size controls and validated CSS-like declarations.
- Add event-driven state/numeric/template/logical visibility with nearest surviving ancestor navigation.
- Add explicit lock/alarm confirmations and keep PIN-protected actions unavailable; drafts remain isolated.
- Add a root-only, selectable settings cog gated by the persisted ESPHome Show Settings switch.

- Rename the shared integration HA Dial Server and explain first-run setup and recovery.
- Remove saved server definitions on integration removal, retain ordinary reloads, and clear live screens on unload with paired firmware.
- Offer installed Dials and Preview in the editor; fix Add subpage on ordinary HTTP.

- Add a dashboard preview zoom setting from 100% to 300%, constrained to the available width.

- Demand-load editor controls and child headings when pages expand; release collapsed branches, retain edits and expansion state, and index children once per tree rebuild.
- Remove HA-wide page/item count, depth and definition-size caps; retain device scene bounds.
- Adopt Casa Mia's calendar version and build numbering, independently of the firmware.
- Use the manifest version for the dashboard card's cache key.

Previous development builds used 0.x versions; the last paired update was 0.4.0.

