from pydantic_settings import SettingsError

from aujobsscraper.config import ScraperSettings


def test_config_parses_json_list_keywords(monkeypatch):
    monkeypatch.setenv(
        "SCRAPER_SEARCH_KEYWORDS",
        '["software engineer","data engineer"]',
    )

    settings = ScraperSettings()

    assert settings.search_keywords == ["software engineer", "data engineer"]


def test_config_rejects_python_style_list(monkeypatch):
    monkeypatch.setenv(
        "SCRAPER_SEARCH_KEYWORDS",
        "['software engineer','data engineer']",
    )

    try:
        ScraperSettings()
        assert False, "Expected list parsing failure for non-JSON env value"
    except SettingsError:
        assert True


def test_indeed_and_prosple_settings_have_defaults():
    settings = ScraperSettings()

    assert settings.indeed_hours_old == 72
    assert settings.indeed_results_wanted == 20
    assert settings.indeed_results_wanted_total == 100
    assert settings.indeed_term_concurrency == 2
    assert settings.indeed_location == ""
    assert settings.indeed_country == "Australia"
    assert settings.prosple_items_per_page == 20
