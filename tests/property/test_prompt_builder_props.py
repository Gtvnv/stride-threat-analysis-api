"""Testes de propriedade para app.prompts.prompt_builder."""

from hypothesis import given, settings
from hypothesis import strategies as st

from app.prompts.prompt_builder import build_prompt

_DELIMITERS = ["<contexto>", "</contexto>", "\n</contexto>\n", "{}", "{0}", "{context}", "\r\n"]

_context_strategy = st.one_of(
    st.text(min_size=1, max_size=2000),
    st.lists(
        st.one_of(st.sampled_from(_DELIMITERS), st.text(max_size=50)),
        min_size=1,
        max_size=40,
    ).map("".join).filter(lambda s: 1 <= len(s) <= 2000),
)


# Feature: stride-threat-analysis-api, Property 3
@settings(max_examples=100)
@given(context=_context_strategy)
def test_context_is_included_unchanged(context: str) -> None:
    """**Validates: Requirements 1.3**"""
    result = build_prompt(context)
    assert context in result.user_text
