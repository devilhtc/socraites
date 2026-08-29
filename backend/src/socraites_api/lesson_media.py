from __future__ import annotations

import html
import re


YOUTUBE_CANDIDATE = re.compile(
    r'<div\b(?=[^>]*\bclass=["\'][^"\']*\byoutube-video\b[^"\']*["\'])[^>]*>\s*</div>',
    flags=re.IGNORECASE,
)
YOUTUBE_BLOCK = re.compile(
    r'<div class="youtube-video" data-video-id="([A-Za-z0-9_-]{11})" '
    r'data-title="([^"\n]{1,160})"(?: data-start="([0-9]{1,6})")?></div>',
)


def render_youtube_embeds(fragment: str) -> str:
    def replace(match: re.Match[str]) -> str:
        exact = YOUTUBE_BLOCK.fullmatch(match.group(0))
        if exact is None:
            return (
                '<div class="youtube-error" role="note"><p>'
                "<strong>Video could not be embedded.</strong> "
                "Check the YouTube lesson markup.</p></div>"
            )
        video_id, raw_title, start = exact.groups()
        if start is not None and int(start) > 86400:
            return (
                '<div class="youtube-error" role="note"><p>'
                "<strong>Video could not be embedded.</strong> "
                "The start time is outside the supported range.</p></div>"
            )
        title = html.escape(html.unescape(raw_title), quote=True)
        query = f"?start={int(start)}" if start is not None and int(start) > 0 else ""
        source = f"https://www.youtube-nocookie.com/embed/{video_id}{query}"
        return (
            '<figure class="youtube-embed">'
            f'<iframe src="{source}" title="{title}" loading="lazy" '
            'referrerpolicy="strict-origin-when-cross-origin" '
            'sandbox="allow-scripts allow-same-origin allow-presentation" '
            'allow="autoplay; encrypted-media; picture-in-picture; fullscreen" '
            'allowfullscreen></iframe>'
            f"<figcaption>{title}</figcaption>"
            "</figure>"
        )

    return YOUTUBE_CANDIDATE.sub(replace, fragment)
