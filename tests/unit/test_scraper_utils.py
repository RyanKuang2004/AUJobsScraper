from aujobsscraper.utils.scraper_utils import remove_html_tags, normalize_locations


def test_remove_html_tags_converts_html_to_markdown_structure():
    html = """
    <div>
      <h2>What You'll Do</h2>
      <ul>
        <li>Build APIs</li>
        <li>Review code</li>
      </ul>
      <h2>What You'll Bring</h2>
      <p>Strong Python skills</p>
    </div>
    """

    result = remove_html_tags(html)

    assert "## What You'll Do" in result
    assert "- Build APIs" in result
    assert "- Review code" in result
    assert "## What You'll Bring" in result
    assert "Strong Python skills" in result


def test_remove_html_tags_converts_strong_to_h2_heading():
    html = "<div><strong>Hi</strong><p>Body text</p></div>"

    result = remove_html_tags(html)

    assert "## Hi" in result
    assert "Body text" in result


def test_normalize_locations_maps_nz_city_to_region():
    result = normalize_locations(["Auckland CBD, Auckland"], country="NZ")
    assert result == [{"city": "Auckland", "state": "Auckland"}]


def test_normalize_locations_handles_nz_city_without_region_suffix():
    result = normalize_locations(["Wellington"], country="NZ")
    assert result == [{"city": "Wellington", "state": "Wellington"}]


def test_normalize_locations_maps_nz_city_to_distinct_region_name():
    result = normalize_locations(["Christchurch"], country="NZ")
    assert result == [{"city": "Christchurch", "state": "Canterbury"}]


def test_normalize_locations_preserves_new_zealand_country_level_location():
    result = normalize_locations(["New Zealand"], country="NZ")
    assert result == [{"city": "New Zealand", "state": ""}]


def test_normalize_locations_filters_out_nz_region_only_string():
    result = normalize_locations(["Waikato"], country="NZ")
    assert result == []


def test_normalize_locations_defaults_to_australia_when_country_not_passed():
    result = normalize_locations(["Sydney"])
    assert result == [{"city": "Sydney", "state": "NSW"}]


def test_normalize_locations_still_handles_australia_when_country_explicit():
    result = normalize_locations(["Fortitude Valley, Brisbane QLD"], country="AU")
    assert result == [{"city": "Brisbane", "state": "QLD"}]


def test_normalize_locations_strips_hybrid_annotation_from_nz_city():
    result = normalize_locations(["Auckland (Hybrid)"], country="NZ")
    assert result == [{"city": "Auckland", "state": "Auckland"}]


def test_normalize_locations_strips_remote_annotation_from_nz_region_only():
    result = normalize_locations(["Waikato (Remote)"], country="NZ")
    assert result == []


def test_normalize_locations_strips_hybrid_annotation_from_nz_comma_separated_city():
    result = normalize_locations(["Wellington Central, Wellington (Hybrid)"], country="NZ")
    assert result == [{"city": "Wellington", "state": "Wellington"}]
