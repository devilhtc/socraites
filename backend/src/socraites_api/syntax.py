from __future__ import annotations

import asyncio
import html
import json
import re
import shutil
import subprocess
from collections import OrderedDict
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path


CODE_BLOCK = re.compile(
    r'<pre><code class="language-([a-z0-9_+-]+)">(.*?)</code></pre>',
    flags=re.IGNORECASE | re.DOTALL,
)


class SyntaxHighlightError(RuntimeError):
    pass


class _HighlightedHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.safe = True

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "span" or len(attrs) != 1 or attrs[0][0] != "class":
            self.safe = False
            return
        classes = (attrs[0][1] or "").split()
        if (
            not classes
            or not classes[0].startswith("hljs-")
            or any(not re.fullmatch(r"[A-Za-z0-9_-]+", value) for value in classes)
        ):
            self.safe = False

    def handle_endtag(self, tag: str) -> None:
        if tag != "span":
            self.safe = False


class SyntaxHighlighter:
    def __init__(self, script_path: Path, *, cache_limit: int = 256) -> None:
        self.script_path = script_path
        self.cache_limit = cache_limit
        self._cache: OrderedDict[str, str] = OrderedDict()

    async def render_fragment(self, fragment: str) -> str:
        matches = list(CODE_BLOCK.finditer(fragment))
        if not matches:
            return fragment

        parts: list[str] = []
        cursor = 0
        for match in matches:
            parts.append(fragment[cursor : match.start()])
            language = match.group(1).lower()
            source = html.unescape(match.group(2))
            try:
                highlighted = await self.highlight(source, language)
                parts.append(
                    f'<pre class="highlighted-code" data-language="{html.escape(language.upper())}">'
                    f'<code class="hljs language-{html.escape(language)}">{highlighted}</code></pre>'
                )
            except SyntaxHighlightError as exc:
                message = html.escape(str(exc)[:240])
                escaped_source = html.escape(source)
                parts.append(
                    '<div class="syntax-error" role="note">'
                    "<p><strong>Syntax highlighting is unavailable.</strong> "
                    f"{message}</p><pre><code>{escaped_source}</code></pre></div>"
                )
            cursor = match.end()
        parts.append(fragment[cursor:])
        return "".join(parts)

    async def highlight(self, source: str, language: str) -> str:
        cache_key = sha256(f"{language}\0{source}".encode("utf-8")).hexdigest()
        if cached := self._cache.get(cache_key):
            self._cache.move_to_end(cache_key)
            return cached

        highlighted = await asyncio.to_thread(self._highlight_uncached, source, language)
        self._cache[cache_key] = highlighted
        self._cache.move_to_end(cache_key)
        while len(self._cache) > self.cache_limit:
            self._cache.popitem(last=False)
        return highlighted

    def _highlight_uncached(self, source: str, language: str) -> str:
        node = shutil.which("node")
        if node is None:
            raise SyntaxHighlightError("Node.js is unavailable. Run the Socraites setup again.")
        if not self.script_path.is_file():
            raise SyntaxHighlightError("The syntax renderer is missing. Run the Socraites setup again.")
        try:
            completed = subprocess.run(
                [node, str(self.script_path)],
                input=json.dumps({"source": source, "language": language}),
                capture_output=True,
                check=False,
                text=True,
                timeout=8,
            )
        except subprocess.TimeoutExpired as exc:
            raise SyntaxHighlightError("Highlighting timed out.") from exc
        if completed.returncode != 0:
            raise SyntaxHighlightError("The syntax renderer stopped unexpectedly.")
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise SyntaxHighlightError("The syntax renderer returned an unreadable result.") from exc
        if not isinstance(payload, dict):
            raise SyntaxHighlightError("The syntax renderer returned an unreadable result.")
        if error := payload.get("error"):
            raise SyntaxHighlightError(str(error))
        highlighted = payload.get("html")
        if not isinstance(highlighted, str):
            raise SyntaxHighlightError("The syntax renderer did not return highlighted code.")
        parser = _HighlightedHTMLParser()
        parser.feed(highlighted)
        if not parser.safe:
            raise SyntaxHighlightError("The highlighted code contains unsupported markup.")
        return highlighted
