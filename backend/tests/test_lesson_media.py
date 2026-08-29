from socraites_api.lesson_media import render_youtube_embeds


def test_youtube_marker_becomes_privacy_enhanced_lazy_embed() -> None:
    rendered = render_youtube_embeds(
        '<div class="youtube-video" data-video-id="M7lc1UVf-VE" '
        'data-title="Player &quot;events&quot;" data-start="45"></div>'
    )

    assert 'src="https://www.youtube-nocookie.com/embed/M7lc1UVf-VE?start=45"' in rendered
    assert 'title="Player &quot;events&quot;"' in rendered
    assert 'loading="lazy"' in rendered
    assert "allowfullscreen" in rendered
    assert '<div class="youtube-video"' not in rendered


def test_invalid_youtube_marker_becomes_readable_error() -> None:
    rendered = render_youtube_embeds(
        '<div class="youtube-video" data-video-id="not-an-id" data-title="Broken"></div>'
    )

    assert "Video could not be embedded." in rendered
    assert "not-an-id" not in rendered


def test_youtube_start_time_is_bounded() -> None:
    rendered = render_youtube_embeds(
        '<div class="youtube-video" data-video-id="M7lc1UVf-VE" '
        'data-title="Too late" data-start="999999"></div>'
    )

    assert "Video could not be embedded." in rendered
    assert "outside the supported range" in rendered
