from app.provider_policies import should_try_next_profile


def test_openrouter_tries_next_profile_on_auth_statuses_only():
    assert should_try_next_profile("openrouter", 401) is True
    assert should_try_next_profile("openrouter", 402) is True
    assert should_try_next_profile("openrouter", 403) is True
    assert should_try_next_profile("openrouter", 429) is False
    assert should_try_next_profile("openrouter", 500) is False
