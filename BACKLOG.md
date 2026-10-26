# Backlog

## P0 — Make first-run setup self-explanatory

Observed on 2026-10-26: the first physical-device setup required repeated AP checks,
serial monitoring, mDNS inspection and a diagnostic reflash. The device accepted captive-
portal credentials, closed its AP, but neither appeared in Home Assistant nor explained
whether Wi-Fi association had failed. This is too painful for a normal installation.

Design and test an initial UX with explicit states:

1. **Starting** — hardware and firmware identity.
2. **Needs Wi-Fi** — show the fallback SSID, password and portal address on-screen.
3. **Connecting** — show the selected SSID without exposing its password.
4. **Wi-Fi failed** — show a useful reason when available and reopen provisioning.
5. **Connected to Wi-Fi** — show the assigned IP address and that HA discovery is pending.
6. **Waiting for HA** — explain that the ESPHome device must be added separately from the
   HA Dial custom integration.
7. **Ready** — replace setup information with the configured navigation screen.

Acceptance criteria:

- A new device can be installed without opening a serial monitor.
- Failed credentials never leave the device with neither a working station connection nor
  an available recovery AP.
- A documented physical gesture clears saved Wi-Fi and reopens provisioning.
- The screen distinguishes Wi-Fi, API and HA-navigation connectivity.
- HA can be added manually using the on-screen IP when mDNS discovery cannot cross a VLAN.
- Provisioning, incorrect-password, unavailable-network, isolated-VLAN and reboot recovery
  paths are tested on the physical Dial v1.1.
- Touch-controller failure is shown separately and does not obscure network status.

Investigate ESPHome Improv Serial/BLE as a second provisioning route, but keep the captive
portal as the dependency-free baseline unless testing proves it unreliable.
