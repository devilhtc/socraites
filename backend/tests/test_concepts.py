import pytest

from socraites_api.concepts import ConceptMarkupError, render_concept_cards
from socraites_api.models import CourseConcept


def test_concept_cards_escape_authored_text_and_keep_visible_term() -> None:
    concept = CourseConcept(
        id="runner",
        name="Runner <host>",
        definition='A "machine" & execution context.',
    )

    rendered = render_concept_cards(
        '<p>One <span class="concept-ref" data-concept-id="runner">runner &amp; host</span>.</p>',
        [concept],
    )

    assert '<dfn class="concept-term" tabindex="0"' in rendered
    assert "runner &amp; host" in rendered
    assert "Runner &lt;host&gt;" in rendered
    assert "A &quot;machine&quot; &amp; execution context." in rendered
    assert "data-concept-id" not in rendered


def test_concept_cards_reject_unknown_ids() -> None:
    fragment = '<span class="concept-ref" data-concept-id="missing">missing term</span>'

    with pytest.raises(ConceptMarkupError, match="unknown concept ids: missing"):
        render_concept_cards(fragment, [])
