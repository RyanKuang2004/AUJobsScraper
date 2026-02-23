import asyncio

from aujobsscraper.scrapers.gradconnection_scraper import GradConnectionScraper


class FakePage:
    def __init__(self, html: str, json_data=None):
        self._html = html
        self._json_data = json_data

    async def goto(self, url, wait_until="domcontentloaded"):
        if not isinstance(url, str):
            raise TypeError("Page.goto: url must be string")
        return None

    async def wait_for_selector(self, selector, timeout=10000):
        return None

    async def content(self):
        return self._html

    async def evaluate(self, _):
        return self._json_data


def test_process_job_accepts_dict_payload_with_url():
    html = """
    <html>
      <body>
        <h1 class="employers-profile-h1">FPGA Engineer Internship</h1>
        <h1 class="employers-panel-title">Citadel Securities</h1>
        <div class="campaign-content-container">
          This is a sufficiently long description for validation.
        </div>
        <ul class="box-content">
          <li><strong>Location</strong> Sydney</li>
        </ul>
      </body>
    </html>
    """

    scraper = GradConnectionScraper()
    page = FakePage(html)

    asyncio.run(
        scraper._process_job(
            page,
            {"url": "https://au.gradconnection.com/employers/citadel/jobs/fpga-internship/"},
        )
    )

    assert len(scraper._results) == 1


def test_process_job_normalizes_gradconnection_salary_dict():
    html = """
    <html>
      <body>
        <h1 class="employers-profile-h1">Graduate Software Engineer</h1>
        <h1 class="employers-panel-title">Example Co</h1>
        <div class="campaign-content-container">
          This is a sufficiently long description for validation.
        </div>
        <ul class="box-content">
          <li><strong>Location</strong> Sydney</li>
        </ul>
      </body>
    </html>
    """
    json_data = {
        "campaignstore": {
            "campaign": {
                "salary": {
                    "min_salary": "60,000",
                    "max_salary": "80,000",
                    "details": "",
                }
            }
        }
    }

    scraper = GradConnectionScraper()
    page = FakePage(html, json_data=json_data)

    asyncio.run(
        scraper._process_job(
            page,
            {"url": "https://au.gradconnection.com/jobs/example"},
        )
    )

    assert len(scraper._results) == 1
    assert scraper._results[0].salary == {"annual_min": 60000.0, "annual_max": 80000.0}
