from config.settings import Settings


def test_settings_defaults_without_key() -> None:
    settings = Settings(_env_file=None)
    assert settings.deepseek_model == "deepseek-chat"
    assert not settings.has_api_key

