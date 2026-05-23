from app.token_budget import estimate_input_tokens, estimate_tokens_from_text


def test_estimate_tokens_uses_conservative_char_division():
    assert estimate_tokens_from_text("abcdef") == 2
    assert estimate_tokens_from_text("abcdefg") == 3


def test_estimate_includes_context():
    result = estimate_input_tokens("abc", {"file": "abcdef"})
    assert result > 1
