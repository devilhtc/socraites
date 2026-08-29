import hljs from "highlight.js/lib/common";

let input = "";
for await (const chunk of process.stdin) {
  input += chunk;
}

try {
  const payload = JSON.parse(input);
  if (typeof payload.source !== "string") {
    throw new Error("The code block has no source text.");
  }
  if (payload.source.length > 20000) {
    throw new Error("Code blocks must not exceed 20,000 characters.");
  }
  if (typeof payload.language !== "string" || !payload.language.trim()) {
    throw new Error("The code block has no language.");
  }
  if (!hljs.getLanguage(payload.language)) {
    throw new Error(`Unsupported syntax language: ${payload.language}`);
  }

  const result = hljs.highlight(payload.source, {
    language: payload.language,
    ignoreIllegals: false,
  });
  process.stdout.write(JSON.stringify({ html: result.value }));
} catch (error) {
  const message = error instanceof Error ? error.message : String(error);
  process.stdout.write(JSON.stringify({ error: message }));
}
