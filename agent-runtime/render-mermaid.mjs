import { renderMermaidSVG } from "beautiful-mermaid";

let input = "";
for await (const chunk of process.stdin) {
  input += chunk;
}

try {
  const payload = JSON.parse(input);
  if (typeof payload.source !== "string" || !payload.source.trim()) {
    throw new Error("The Mermaid block is empty.");
  }
  if (payload.source.length > 20000) {
    throw new Error("Mermaid blocks must not exceed 20,000 characters.");
  }
  if (/^\s*%%\{/m.test(payload.source) || /^\s*click\s+/im.test(payload.source)) {
    throw new Error("Mermaid configuration and click directives are not supported in lessons.");
  }

  const svg = renderMermaidSVG(payload.source, {
    bg: "var(--page)",
    fg: "var(--body)",
    line: "var(--muted)",
    accent: "var(--accent)",
    surface: "var(--panel)",
    border: "var(--line)",
    font: "ui-sans-serif, system-ui, sans-serif",
    transparent: true,
  }).replace(/\s*@import\s+url\([^;]+;?/gi, "");

  process.stdout.write(JSON.stringify({ svg }));
} catch (error) {
  const message = error instanceof Error ? error.message : String(error);
  process.stdout.write(JSON.stringify({ error: message }));
}
