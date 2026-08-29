import asyncio
from pathlib import Path

from socraites_api.mermaid import MermaidRenderer


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_renderer_replaces_mermaid_block_with_local_svg() -> None:
    renderer = MermaidRenderer(PROJECT_ROOT / "agent-runtime" / "render-mermaid.mjs")

    rendered = asyncio.run(renderer.render_fragment(
        '<p>Before.</p><pre class="mermaid">flowchart LR\n  A --> B</pre><p>After.</p>'
    ))

    assert '<figure class="mermaid-diagram"' in rendered
    assert "<svg" in rendered
    assert '<pre class="mermaid">' not in rendered
    assert "fonts.googleapis.com" not in rendered
    assert "<p>Before.</p>" in rendered
    assert "<p>After.</p>" in rendered


def test_renderer_keeps_lesson_readable_when_mermaid_is_invalid() -> None:
    renderer = MermaidRenderer(PROJECT_ROOT / "agent-runtime" / "render-mermaid.mjs")

    rendered = asyncio.run(renderer.render_fragment(
        '<pre class="mermaid">not-a-diagram</pre>'
    ))

    assert "Diagram could not be rendered." in rendered
    assert "not-a-diagram" in rendered


def test_renderer_rejects_mermaid_configuration_directives() -> None:
    renderer = MermaidRenderer(PROJECT_ROOT / "agent-runtime" / "render-mermaid.mjs")

    rendered = asyncio.run(renderer.render_fragment(
        '<pre class="mermaid">%%{init: {"theme": "dark"}}%%\nflowchart LR\n  A --> B</pre>'
    ))

    assert "Diagram could not be rendered." in rendered
    assert "configuration and click directives are not supported" in rendered
