from bs4 import BeautifulSoup

# Read both HTML files
with open("debug_gc_initial.html", 'r', encoding='utf-8') as f:
    initial_content = f.read()
    
with open("debug_gc_after_click.html", 'r', encoding='utf-8') as f:
    after_content = f.read()

initial_soup = BeautifulSoup(initial_content, 'lxml')
after_soup = BeautifulSoup(after_content, 'lxml')

# Find the locations li in both
for name, soup in [("INITIAL", initial_soup), ("AFTER CLICK", after_soup)]:
    print(f"\n{'='*60}")
    print(f"{name}")
    print('='*60)
    
    box_content = soup.select_one("ul.box-content")
    if box_content:
        for li in box_content.find_all("li"):
            strong = li.find("strong")
            if strong and "location" in strong.text.lower():
                print(f"\nFull HTML for locations li:")
                print(li.prettify()[:1500])
                print("\n...")
                break
