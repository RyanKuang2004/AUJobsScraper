"""AUJobsScraper - Australian job board scrapers."""

from importlib import import_module

__all__ = [
    "JobPosting",
    "Location",
    "SeekScraper",
    "GradConnectionScraper",
    "ProspleScraper",
    "IndeedScraper",
]

_EXPORT_TO_MODULE = {
    "JobPosting": "aujobsscraper.models.job",
    "Location": "aujobsscraper.models.location",
    "SeekScraper": "aujobsscraper.scrapers.seek_scraper",
    "GradConnectionScraper": "aujobsscraper.scrapers.gradconnection_scraper",
    "ProspleScraper": "aujobsscraper.scrapers.prosple_scraper",
    "IndeedScraper": "aujobsscraper.scrapers.indeedscraper",
}


def __getattr__(name: str):
    module_name = _EXPORT_TO_MODULE.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(module_name)
    value = getattr(module, name)
    globals()[name] = value
    return value
