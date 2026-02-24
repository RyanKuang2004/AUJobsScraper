from importlib import import_module

__all__ = ["BaseScraper", "SeekScraper", "GradConnectionScraper", "ProspleScraper", "IndeedScraper"]

_CLASS_TO_MODULE = {
    "BaseScraper": "base_scraper",
    "SeekScraper": "seek_scraper",
    "GradConnectionScraper": "gradconnection_scraper",
    "ProspleScraper": "prosple_scraper",
    "IndeedScraper": "indeed_scraper",
}


def __getattr__(name: str):
    module_name = _CLASS_TO_MODULE.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(f"{__name__}.{module_name}")
    value = getattr(module, name)
    globals()[name] = value
    return value
