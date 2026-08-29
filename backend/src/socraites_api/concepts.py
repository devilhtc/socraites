from __future__ import annotations

import html
import re
from collections.abc import Iterable

from .models import CourseConcept


CONCEPT_REF = re.compile(
    r'<span class="concept-ref" data-concept-id="([a-z0-9][a-z0-9-]*)">([^<>\n]+)</span>'
)
CONCEPT_MARKER = re.compile(
    r'<span\b[^>]*\bclass=["\'][^"\']*\bconcept-ref\b',
    flags=re.IGNORECASE,
)


class ConceptMarkupError(ValueError):
    pass


def concept_references(fragment: str) -> list[str]:
    matches = list(CONCEPT_REF.finditer(fragment))
    if len(matches) != len(CONCEPT_MARKER.findall(fragment)):
        raise ConceptMarkupError(
            'concept references must use <span class="concept-ref" '
            'data-concept-id="concept-id">visible term</span>'
        )
    return [match.group(1) for match in matches]


def validate_concept_references(fragment: str, concepts: Iterable[CourseConcept]) -> list[str]:
    references = concept_references(fragment)
    known = {concept.id for concept in concepts}
    unknown = sorted(set(references) - known)
    if unknown:
        raise ConceptMarkupError(f"unknown concept ids: {', '.join(unknown)}")
    return references


def render_concept_cards(fragment: str, concepts: Iterable[CourseConcept]) -> str:
    concept_index = {concept.id: concept for concept in concepts}
    validate_concept_references(fragment, concept_index.values())
    occurrence = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal occurrence
        occurrence += 1
        concept = concept_index[match.group(1)]
        card_id = f"concept-card-{concept.id}-{occurrence}"
        visible_term = html.escape(html.unescape(match.group(2)), quote=False)
        return (
            f'<dfn class="concept-term" tabindex="0" aria-describedby="{card_id}">'
            f'{visible_term}<span class="concept-card" id="{card_id}" role="tooltip">'
            f'<strong class="concept-card-title">{html.escape(concept.name)}</strong>'
            f'<span class="concept-card-definition">{html.escape(concept.definition)}</span>'
            "</span></dfn>"
        )

    return CONCEPT_REF.sub(replace, fragment)
