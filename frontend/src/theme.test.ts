import { describe, expect, it } from "vitest";
import { contrastText, DEFAULT_PALETTE, paletteName, paletteTokens, restorePalette, themeMode } from "./theme";

describe("appearance palettes", () => {
  it("detects light and dark backgrounds", () => {
    expect(themeMode("#f4efe5")).toBe("light");
    expect(themeMode("#11110f")).toBe("dark");
  });

  it("derives interface tokens from custom colors", () => {
    const tokens = paletteTokens({ presetId: null, background: "#101820", accent: "#42d6c3" });
    expect(tokens["--page"]).toBe("#101820");
    expect(tokens["--accent"]).toBe("#42d6c3");
    expect(tokens["--surface"]).not.toBe(tokens["--page"]);
  });

  it("chooses whichever black or white text has greater accent contrast", () => {
    expect(contrastText("#a85f16")).toBe("#ffffff");
    expect(contrastText("#f3b85c")).toBe("#000000");
    expect(paletteTokens(DEFAULT_PALETTE)["--accent-ink"]).toBe("#ffffff");
  });

  it("restores a saved custom palette and rejects malformed storage", () => {
    const custom = restorePalette('{"presetId":null,"background":"#123456","accent":"#abcdef"}', null, false);
    expect(custom).toEqual({ presetId: null, background: "#123456", accent: "#abcdef" });
    expect(paletteName(custom)).toBe("Custom Mix");
    expect(restorePalette("not-json", "light", true)).toEqual({
      presetId: DEFAULT_PALETTE.presetId,
      background: DEFAULT_PALETTE.background,
      accent: DEFAULT_PALETTE.accent,
    });
  });

  it("refreshes stored presets to their current colors", () => {
    expect(restorePalette(
      '{"presetId":"parchment-ember","background":"#f4efe5","accent":"#b5661a"}',
      null,
      false,
    )).toEqual({
      presetId: "parchment-ember",
      background: "#fbf7ee",
      accent: "#a85f16",
    });
  });
});
