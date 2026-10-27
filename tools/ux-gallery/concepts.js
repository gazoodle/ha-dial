export const themes = [
  { id: "ember", name: "Ember", bg: "#060707", surface: "#15110f", primary: "#ff8b2d", secondary: "#ffd19a", quiet: "#77513a", text: "#fff7eb", grid: "#3a2920" },
  { id: "verdant", name: "Verdant", bg: "#030a09", surface: "#071815", primary: "#66f7ba", secondary: "#b9ffe2", quiet: "#2a6655", text: "#effff8", grid: "#153b32" },
  { id: "cobalt", name: "Cobalt", bg: "#050711", surface: "#0b1025", primary: "#5aa8ff", secondary: "#b7c9ff", quiet: "#32477b", text: "#f4f6ff", grid: "#1c2a55" },
  { id: "rose", name: "Rosé", bg: "#0b0608", surface: "#201015", primary: "#ff719e", secondary: "#ffd0c2", quiet: "#76384d", text: "#fff3f5", grid: "#46222f" },
  { id: "acid", name: "Acid", bg: "#070904", surface: "#151a0a", primary: "#c9ff45", secondary: "#fff186", quiet: "#5c7425", text: "#fbffe9", grid: "#344214" },
  { id: "alloy", name: "Alloy", bg: "#060708", surface: "#181b1f", primary: "#e4e9ed", secondary: "#8fd8ff", quiet: "#59636c", text: "#ffffff", grid: "#30363c" },
];

const navigation = [
  ["orbit", "Orbital index", "Large destinations orbit the outside while fixed Back and Home controls remain inside."],
  ["pointer", "Pointer ring", "An inner-ring pointer aims outward at large peripheral icons, preserving display centricity."],
  ["rolodex", "Perspective rolodex", "A tactile vertical carousel bends neighbouring destinations away from the viewer."],
  ["petals", "Petal sectors", "Destinations become instrument-like radial sectors with a strong central label."],
  ["constellation", "Connected constellation", "A spatial map joins destinations with fine routes and lights the active node."],
  ["compass", "Four-way compass", "Four large choices use the display like a directional instrument."],
  ["ribbon", "Ribbon carousel", "A diagonal ribbon carries destinations past a fixed selection aperture."],
  ["breadcrumb", "Layered breadcrumb", "The current place dominates while ancestors and children form architectural layers."],
];

const domains = [
  ["light", "Lighting", "Brightness, warmth and power with a luminous radial language."],
  ["thermostat", "Climate", "Target temperature, ambient temperature and mode without dashboard chrome."],
  ["media", "Now playing", "Artwork, transport and progress arranged for quick physical control."],
  ["volume", "Volume", "A tactile level control with waveform and confirmed-state detail."],
  ["cover", "Blinds & covers", "Position and direction presented as architectural movement."],
  ["fan", "Fan", "Speed, mode and airflow expressed through a turbine-like centre."],
  ["security", "Security", "Arm state and sensor summary with sober, high-confidence hierarchy."],
  ["lock", "Access", "Lock state, activity and primary action with physical-instrument character."],
  ["vacuum", "Cleaning", "Map progress, remaining area and dock state in a compact mission display."],
  ["energy", "Energy", "Live demand and generation balance with dense but legible instrumentation."],
  ["weather", "Weather", "Current conditions with compact forecast and environmental detail."],
  ["air", "Air quality", "AQI, particulates and ventilation state as a calm environmental gauge."],
  ["timer", "Timer", "Elapsed or remaining time with a dominant rotary-adjustable ring."],
  ["calendar", "Agenda", "The next event and day density fitted into a glanceable circular schedule."],
  ["vehicle", "Vehicle & charging", "Range, charging power and readiness in a technical cluster."],
  ["water", "Water", "Flow, tank level and consumption with liquid depth cues."],
  ["scene", "Scenes", "Atmosphere-first scene selection using composed miniature environments."],
  ["selector", "Selector", "A general-purpose option wheel for modes, sources and presets."],
];

const specials = {
  chronograph: [
    ["tricompax", "Tricompax nocturne", "Three recessed complications, a minute track and strong luminous hands."],
    ["worldtimer", "World-time instrument", "City ring, dual time, date and power reserve layered around a clear centre."],
    ["skeleton", "Open-work regulator", "Visible geometric movement, asymmetric registers and restrained technical type."],
    ["moonphase", "Perpetual moon", "Moon phase, calendar and small seconds arranged like a dress chronograph."],
  ],
  smartwatch: [
    ["contour", "Edge numerals", "Expressive numerals follow the circular boundary while the centre remains calm and useful."],
    ["modular", "Complication deck", "Time and three information-rich complications form a disciplined glanceable stack."],
    ["palette", "Chromatic stack", "Layered colour bands turn the passing day into an architectural composition."],
    ["rings", "Daily rings", "Three bold progress rings surround compact movement, energy and standing summaries."],
    ["solar", "Daylight horizon", "A sculpted horizon and moving light field make the sun's position immediately legible."],
    ["reflections", "Machined light", "Metallic radial forms catch imaginary light without imitating a mechanical dial."],
    ["photos", "Photo time", "A full-bleed photograph carries restrained typography and two tiny complications."],
    ["toybox", "Toybox adventure", "An original cowboy-and-space-toy tableau brings a little animated-character mischief."],
  ],
  data: [
    ["area", "Layered area", "A luminous filled trace with live value, range and event markers."],
    ["radar", "Radial telemetry", "Several measures share a polar plot suited to the circular display."],
    ["bands", "Concentric bands", "Current, target and historic ranges become nested instrument tracks."],
    ["spark", "Micro-dashboard", "Four compact metrics support one dominant sparkline without losing hierarchy."],
  ],
  camera: [
    ["portal", "Portal snapshot", "A clean live snapshot with event type, age and two direct actions."],
    ["cinema", "Cinematic crop", "A wide crop floats inside the circle with quiet status typography."],
    ["radar", "Security radar", "Snapshot, detection zones and event confidence form an analytical camera view."],
  ],
  ambient: [
    ["solar", "Solar ephemeris", "Time, daylight arc, sunrise, sunset and weather create a calm ambient face."],
    ["typographic", "Typographic time", "Oversized numerals carry the screen while fine details reward a closer look."],
    ["orbital", "Orbital clock", "Time and date sit inside slowly layered astronomical tracks."],
    ["status", "House pulse", "Time remains primary while tiny complications summarise the home at rest."],
  ],
};

const concepts = [];

for (const theme of themes) {
  for (const [layout, title, description] of navigation) {
    concepts.push({ id: `NAV-${layout}-${theme.id}`.toUpperCase(), family: "Navigation", kind: "navigation", layout, title, description, theme });
  }
  for (const [domain, title, description] of domains) {
    for (const variant of ["instrument", "editorial"]) {
      concepts.push({
        id: `CTL-${domain}-${variant}-${theme.id}`.toUpperCase(),
        family: "Domain controls",
        kind: "control",
        domain,
        variant,
        title: `${title} · ${variant}`,
        description,
        theme,
      });
    }
  }
  for (const [kind, entries] of Object.entries(specials)) {
    for (const [layout, title, description] of entries) {
      const prefix = kind === "smartwatch" ? "WAT" : kind.slice(0, 3);
      concepts.push({ id: `${prefix}-${layout}-${theme.id}`.toUpperCase(), family: kind[0].toUpperCase() + kind.slice(1), kind, layout, title, description, theme });
    }
  }
}

export { concepts };
