# tests/unit/test_models.py
import pytest
from aujobsscraper.models.job import JobPosting
from aujobsscraper.models.location import Location


def test_job_posting_requires_title():
    with pytest.raises(Exception):
        JobPosting(company="Acme", description="A job")


def test_job_posting_auto_fingerprint():
    job = JobPosting(
        job_title="Software Engineer",
        company="Acme",
        description="Build great software",
        locations=[Location(city="Sydney", state="NSW")],
        source_urls=["https://example.com/job/1"],
        platforms=["seek"],
    )
    assert job.fingerprint is not None
    assert len(job.fingerprint) == 32  # MD5 hex


def test_job_posting_fingerprint_stable():
    kwargs = dict(
        job_title="Software Engineer",
        company="Acme",
        description="Build great software",
        locations=[Location(city="Sydney", state="NSW")],
        source_urls=["https://example.com/job/1"],
        platforms=["seek"],
    )
    job1 = JobPosting(**kwargs)
    job2 = JobPosting(**kwargs)
    assert job1.fingerprint == job2.fingerprint


def test_job_posting_validate_missing_location():
    job = JobPosting(
        job_title="Dev",
        company="Corp",
        description="Some description here",
        source_urls=["https://example.com/1"],
        platforms=["seek"],
    )
    errors = job.validate()
    assert any("location" in e.lower() for e in errors)


def test_job_posting_validate_ok():
    job = JobPosting(
        job_title="Dev",
        company="Corp",
        description="Some description here",
        locations=[Location(city="Melbourne", state="VIC")],
        source_urls=["https://example.com/1"],
        platforms=["seek"],
    )
    assert job.validate() == []


def test_job_posting_to_dict_serializes_locations():
    job = JobPosting(
        job_title="Dev",
        company="Corp",
        description="Some description here",
        locations=[Location(city="Brisbane", state="QLD")],
        source_urls=["https://example.com/1"],
        platforms=["seek"],
    )
    d = job.to_dict()
    assert d["locations"] == [{"city": "Brisbane", "state": "QLD"}]


def test_job_posting_has_no_llm_fields():
    job = JobPosting(
        job_title="Dev",
        company="Corp",
        description="Some description here",
        locations=[Location(city="Perth", state="WA")],
        source_urls=["https://example.com/1"],
        platforms=["seek"],
    )
    d = job.to_dict()
    assert "job_role" not in d
    assert "seniority" not in d
    assert "core_languages" not in d
    assert "llm_extracted_at" not in d
