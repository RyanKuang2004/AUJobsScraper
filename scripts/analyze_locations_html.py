import re
from bs4 import BeautifulSoup

# Read the after-click HTML
with open("debug_gc_after_click.html", 'r', encoding='utf-8') as f:
    content = f.read()

soup = BeautifulSoup(content, 'lxml')

# Look for the box-content ul
box_content = soup.select_one("ul.box-content")
if box_content:
    print("Found ul.box-content")
    for li in box_content.find_all("li"):
        strong = li.find("strong")
        if strong and "location" in strong.text.lower():
            print(f"\nFound locations li:")
            print(f"Full li text: {li.text[:300]}")
            
            # Check for ellipsis-text-paragraph div
            ellipsis_div = li.find("div", class_="ellipsis-text-paragraph")
            if ellipsis_div:
                print(f"\nFound ellipsis-text-paragraph div:")
                print(f"Text: {ellipsis_div.text[:300]}")
            
            # Check for show-more button in this li
            show_more_btn = li.find("button", class_="show-more")
            if show_more_btn:
                print(f"\nFound show-more button: {show_more_btn.text}")
            
            show_less_btn = li.find("button", class_="show-less")
            if show_less_btn:
                print(f"\nFound show-less button: {show_less_btn.text}")
                
            # Get all text from the div
            div = li.find("div")
            if div:
                # Get all text including from nested elements
                all_text = div.get_text(separator=", ", strip=True)
                print(f"\nAll text from div: {all_text[:500]}")
