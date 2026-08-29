export type ThemeMode = "light" | "dark";

export type Palette = {
  presetId: string | null;
  accent: string;
  background: string;
};

export type PalettePreset = Palette & {
  presetId: string;
  name: string;
};

export const PALETTE_PRESETS: PalettePreset[] = [
  { presetId: "parchment-ember", name: "Parchment Ember", background: "#fbf7ee", accent: "#a85f16" },
  { presetId: "carbon-gold", name: "Carbon Gold", background: "#11110f", accent: "#f3b85c" },
  { presetId: "neon-fjord", name: "Neon Fjord", background: "#0d1b24", accent: "#38c6b4" },
  { presetId: "orchid-after-dark", name: "Orchid After Dark", background: "#1a1424", accent: "#c99bff" },
  { presetId: "alpine-terminal", name: "Alpine Terminal", background: "#edf3ef", accent: "#247a63" },
  { presetId: "coral-blueprint", name: "Coral Blueprint", background: "#eef4fb", accent: "#d85d45" },
];

export const DEFAULT_PALETTE = PALETTE_PRESETS[0];

const HEX_COLOR = /^#[0-9a-f]{6}$/i;

function rgb(color: string): [number, number, number] {
  return [
    Number.parseInt(color.slice(1, 3), 16),
    Number.parseInt(color.slice(3, 5), 16),
    Number.parseInt(color.slice(5, 7), 16),
  ];
}

function hex(channels: [number, number, number]): string {
  return `#${channels.map((channel) => Math.round(channel).toString(16).padStart(2, "0")).join("")}`;
}

export function mixHex(base: string, overlay: string, overlayWeight: number): string {
  const baseChannels = rgb(base);
  const overlayChannels = rgb(overlay);
  return hex(baseChannels.map((channel, index) => (
    channel * (1 - overlayWeight) + overlayChannels[index] * overlayWeight
  )) as [number, number, number]);
}

export function themeMode(background: string): ThemeMode {
  const channels = rgb(background).map((channel) => {
    const normalized = channel / 255;
    return normalized <= 0.04045
      ? normalized / 12.92
      : ((normalized + 0.055) / 1.055) ** 2.4;
  });
  const luminance = channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
  return luminance < 0.38 ? "dark" : "light";
}

export function paletteName(palette: Palette): string {
  return PALETTE_PRESETS.find((preset) => preset.presetId === palette.presetId)?.name ?? "Custom Mix";
}

export function paletteTokens(palette: Palette): Record<string, string> {
  const mode = themeMode(palette.background);
  const dark = mode === "dark";
  return {
    "--page": palette.background,
    "--surface": mixHex(palette.background, dark ? "#ffffff" : "#000000", dark ? 0.06 : 0.035),
    "--surface-raised": mixHex(palette.background, dark ? "#ffffff" : "#ffffff", dark ? 0.10 : 0.62),
    "--surface-soft": mixHex(palette.background, dark ? "#ffffff" : "#000000", dark ? 0.13 : 0.08),
    "--ink": mixHex(palette.background, dark ? "#ffffff" : "#000000", dark ? 0.94 : 0.87),
    "--body": mixHex(palette.background, dark ? "#ffffff" : "#000000", dark ? 0.78 : 0.66),
    "--muted": mixHex(palette.background, dark ? "#ffffff" : "#000000", dark ? 0.58 : 0.53),
    "--line": mixHex(palette.background, dark ? "#ffffff" : "#000000", dark ? 0.14 : 0.14),
    "--accent": palette.accent,
    "--accent-strong": mixHex(palette.accent, dark ? "#ffffff" : "#000000", dark ? 0.24 : 0.22),
    "--accent-soft": mixHex(palette.background, palette.accent, dark ? 0.24 : 0.20),
    "--shadow": dark ? "0 18px 60px rgba(0,0,0,.3)" : "0 18px 50px rgba(31,38,45,.1)",
  };
}

export function restorePalette(saved: string | null, legacyTheme: string | null, prefersDark: boolean): Palette {
  if (saved) {
    try {
      const value = JSON.parse(saved) as Partial<Palette>;
      if (typeof value.accent === "string" && HEX_COLOR.test(value.accent)
        && typeof value.background === "string" && HEX_COLOR.test(value.background)
        && (typeof value.presetId === "string" || value.presetId === null)) {
        const preset = PALETTE_PRESETS.find((item) => item.presetId === value.presetId);
        if (preset) {
          return { presetId: preset.presetId, accent: preset.accent, background: preset.background };
        }
        return {
          presetId: value.presetId ?? null,
          accent: value.accent.toLowerCase(),
          background: value.background.toLowerCase(),
        };
      }
    } catch {
      // Fall through to the legacy preference or system preference.
    }
  }
  const fallback = legacyTheme === "dark" || (!legacyTheme && prefersDark)
    ? PALETTE_PRESETS[1]
    : DEFAULT_PALETTE;
  return { presetId: fallback.presetId, accent: fallback.accent, background: fallback.background };
}
