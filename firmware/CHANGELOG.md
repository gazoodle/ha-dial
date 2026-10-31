# HA Dial firmware changelog

## 2026.10.1-b4

- Add scene version 5: filled polygons, multi-line segments, solid bands, round caps and integer coverage blending against a declared colour. Larger masks and digit cells are accepted. Requires HA Dial Server 2026.10.1-b10.

## 2026.10.1-b3

- Accept scene v4 bounded polylines, reject invalid points and join HA-supplied geometry with the shared Bresenham raster. Retain v1–v3 support.

## 2026.10.1-b2

- Accept scene v3 signed/decimal glyph feedback and normalised gauge ranges, retaining v1/v2 support.
- Guard restored settings callbacks until UI startup, retain power-hold setup order and give reset confirmation priority over settings input.
- Add persistent Show Settings config switch, root settings handshake and local IP/version/uptime/network/touch diagnostics.
- Keep settings available from the offline fallback only when enabled; disabling closes it, and physical Wi-Fi recovery remains independent.

## 2026.10.1-b1

- Add network/API/HA setup guidance, local confirmed Wi-Fi reset and native restart/recovery buttons.
- Hide cached screens on disconnect and honour revision-checked server screen-clear commands.

- Adopt Casa Mia's calendar version and build numbering, independently of HA Dial Server.
- Expose Firmware Version as an ESPHome diagnostic text sensor, published once at boot.
- Report the same version in ESPHome project metadata and the startup screen.

Previous development builds used 0.x versions; the last paired update was 0.4.0.
