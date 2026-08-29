import asyncio
from pathlib import Path

from socraites_api.syntax import SyntaxHighlighter


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_highlighter_replaces_language_code_with_safe_token_markup() -> None:
    highlighter = SyntaxHighlighter(PROJECT_ROOT / "agent-runtime" / "render-code.mjs")

    rendered = asyncio.run(highlighter.render_fragment(
        '<pre><code class="language-js">const answer = await learn();</code></pre>'
    ))

    assert '<pre class="highlighted-code" data-language="JS">' in rendered
    assert 'class="hljs-keyword"' in rendered
    assert 'class="hljs-keyword">await</span>' in rendered
    assert "<script" not in rendered


def test_highlighter_escapes_code_and_handles_unknown_languages() -> None:
    highlighter = SyntaxHighlighter(PROJECT_ROOT / "agent-runtime" / "render-code.mjs")

    rendered = asyncio.run(highlighter.render_fragment(
        '<pre><code class="language-madeup">&lt;unsafe&gt;</code></pre>'
    ))

    assert "Syntax highlighting is unavailable." in rendered
    assert "Unsupported syntax language: madeup" in rendered
    assert "&lt;unsafe&gt;" in rendered
    assert "<unsafe>" not in rendered
