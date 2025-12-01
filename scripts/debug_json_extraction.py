import re
import json

# Read the HTML file
with open("debug_gc_after_click.html", 'r', encoding='utf-8') as f:
    content = f.read()

# Find script tags
from bs4 import BeautifulSoup
soup = BeautifulSoup(content, 'lxml')
script_tags = soup.find_all("script")

for i, script in enumerate(script_tags):
    if script.string and "window.__initialState__" in script.string:
        print(f"Found script tag {i} with window.__initialState__")
        script_content = script.string
        
        # Try different regex patterns
        patterns = [
            r'window\.__initialState__\s*=\s*({.+?});?\s*$',
            r'window\.__initialState__\s*=\s*({.+});',
            r'window\.__initialState__\s*=\s*(\{[\s\S]+\});',
        ]
        
        for j, pattern in enumerate(patterns):
            print(f"\n--- Testing pattern {j}: {pattern[:50]}... ---")
            match = re.search(pattern, script_content, re.DOTALL)
            if match:
                json_str = match.group(1)
                print(f"Matched! JSON string length: {len(json_str)}")
                print(f"First 200 chars: {json_str[:200]}")
                print(f"Last 200 chars: ...{json_str[-200:]}")
                
                try:
                    json_data = json.loads(json_str)
                    print("JSON parsed successfully!")
                    
                    # Try to extract locations
                    job_details = json_data.get("jobDetails", {}).get("job", {})
                    locations = job_details.get("locations", [])
                    print(f"Locations: {locations[:5]}...")  # First 5
                    break
                except Exception as e:
                    print(f"JSON parsing failed: {e}")
            else:
                print("No match")
        else:
            continue
        break
