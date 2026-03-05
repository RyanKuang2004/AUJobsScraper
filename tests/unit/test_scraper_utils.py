from aujobsscraper.utils.scraper_utils import remove_html_tags


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
