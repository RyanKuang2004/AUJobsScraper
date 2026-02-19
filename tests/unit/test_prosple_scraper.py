import asyncio

from aujobsscraper.scrapers.prosple_scraper import ProspleScraper


class FakePage:
    def __init__(self, html: str):
        self._html = html

    async def goto(self, url, wait_until="domcontentloaded"):
        return None

    async def content(self):
        return self._html


def test_get_job_links_extracts_target_blank_graduate_employer_links(monkeypatch):
    html = """
    <html>
      <body>
        <a target="_blank" href="/graduate-employers/acme/jobs-internships/software-engineer-123">Match 1</a>
        <a target="_blank" href="/graduate-employers/contoso/jobs-internships/data-engineer-456">Match 2</a>
        <a target="_self" href="/graduate-employers/ignored/jobs-internships/nope">Ignore target</a>
        <a target="_blank" href="/not-graduate-employers/ignored">Ignore prefix</a>
      </body>
    </html>
    """

    async def _no_sleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", _no_sleep)

    scraper = ProspleScraper()
    page = FakePage(html)

    jobs = asyncio.run(scraper._get_job_links(page, "https://au.prosple.com/search-jobs"))
    assert jobs == [
        {"url": "https://au.prosple.com/graduate-employers/acme/jobs-internships/software-engineer-123"},
        {"url": "https://au.prosple.com/graduate-employers/contoso/jobs-internships/data-engineer-456"},
    ]


def test_extract_salary_returns_dict_from_json_ld_quantitative_value():
    scraper = ProspleScraper()
    json_data = {
        "baseSalary": {
            "@type": "MonetaryAmount",
            "currency": "AUD",
            "value": {
                "@type": "QuantitativeValue",
                "unitText": "YEAR",
                "minValue": 50000,
                "maxValue": 56000,
            },
        }
    }

    salary = scraper._extract_salary(None, json_data)
    assert salary == {"annual_min": 50000.0, "annual_max": 56000.0}
