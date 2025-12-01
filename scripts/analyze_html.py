
import os

def analyze_file(filename, keywords):
    print(f"Analyzing {filename}...")
    if not os.path.exists(filename):
        print(f"File {filename} not found.")
        return

    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    for keyword in keywords:
        index = content.lower().find(keyword.lower())
        if index != -1:
            print(f"Found '{keyword}' at index {index}")
            
            # Find nearest <script before index
            script_start = content.rfind("<script", 0, index)
            if script_start != -1:
                print(f"Nearest <script found at {script_start}")
                print(f"Script tag start: {content[script_start:script_start+100]}...")
            else:
                print("No <script tag found before match.")
            
            # Print some context around the match
            start = max(0, index - 100)
            end = min(len(content), index + 300)
            snippet = content[start:end].replace('\n', '\\n')
            print(f"Context: ...{snippet}...")
            print("-" * 50)

if __name__ == "__main__":
    keywords = ["customer_organization_id"]
    analyze_file("debug_gc_after_click.html", keywords)
