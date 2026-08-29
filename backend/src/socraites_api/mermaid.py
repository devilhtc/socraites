from __future__ import annotations

import asyncio
import html
import json
import re
import shutil
import subprocess
from collections import OrderedDict
from hashlib import sha256
from pathlib import Path


MERMAID_BLOCK = re.compile(
    r'<pre class="mermaid">\s*(.*?)\s*</pre>',
    flags=re.IGNORECASE | re.DOTALL,
)
UNSAFE_SVG = re.compile(
    r"<(?:script|foreignObject|iframe|object|embed|image)\b|"
    r"\son[a-z]+\s*=|"
    r"(?:href|src)\s*=\s*[\"']\s*(?:https?:|//|javascript:|data:)|"
    r"javascript:|url\s*\(\s*[\"']?\s*(?:https?:|//|data:)",
    flags=re.IGNORECASE,
)


class MermaidRenderError(RuntimeError):
    pass


class MermaidRenderer:
    def __init__(self, script_path: Path, *, cache_limit: int = 128) -> None:
        self.script_path = script_path
        self.cache_limit = cache_limit
        self._cache: OrderedDict[str, str] = OrderedDict()

    async def render_fragment(self, fragment: str) -> str:
        matches = list(MERMAID_BLOCK.finditer(fragment))
        if not matches:
            return fragment

        parts: list[str] = []
        cursor = 0
        for match in matches:
            parts.append(fragment[cursor : match.start()])
            source = html.unescape(match.group(1)).strip()
            try:
                svg = await self.render(source)
                parts.append(
                    '<figure class="mermaid-diagram" role="img" '
                    'aria-label="Diagram">'
                    f"{svg}</figure>"
                )
            except MermaidRenderError as exc:
                message = html.escape(str(exc)[:240])
                escaped_source = html.escape(source)
                parts.append(
                    '<div class="mermaid-error" role="note">'
                    "<p><strong>Diagram could not be rendered.</strong> "
                    f"{message}</p><pre><code>{escaped_source}</code></pre></div>"
                )
            cursor = match.end()
        parts.append(fragment[cursor:])
        return "".join(parts)

    async def render(self, source: str) -> str:
        cache_key = sha256(source.encode("utf-8")).hexdigest()
        if cached := self._cache.get(cache_key):
            self._cache.move_to_end(cache_key)
            return cached

        svg = await asyncio.to_thread(self._render_uncached, source)
        self._cache[cache_key] = svg
        self._cache.move_to_end(cache_key)
        while len(self._cache) > self.cache_limit:
            self._cache.popitem(last=False)
        return svg

    def _render_uncached(self, source: str) -> str:
        node = shutil.which("node")
        if node is None:
            raise MermaidRenderError("Node.js is unavailable. Run the Socraites setup again.")
        if not self.script_path.is_file():
            raise MermaidRenderError("The Mermaid renderer is missing. Run the Socraites setup again.")
        try:
            completed = subprocess.run(
                [node, str(self.script_path)],
                input=json.dumps({"source": source}),
                capture_output=True,
                check=False,
                text=True,
                timeout=8,
            )
        except subprocess.TimeoutExpired as exc:
            raise MermaidRenderError("Rendering timed out.") from exc
        if completed.returncode != 0:
            raise MermaidRenderError("The renderer stopped unexpectedly.")
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise MermaidRenderError("The renderer returned an unreadable result.") from exc
        if not isinstance(payload, dict):
            raise MermaidRenderError("The renderer returned an unreadable result.")
        if error := payload.get("error"):
            raise MermaidRenderError(str(error))
        svg = payload.get("svg")
        if not isinstance(svg, str) or not svg.lstrip().startswith("<svg"):
            raise MermaidRenderError("The renderer did not return an SVG.")
        if UNSAFE_SVG.search(svg):
            raise MermaidRenderError("The rendered SVG contains unsupported content.")
        return svg
