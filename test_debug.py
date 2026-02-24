import re

# Test different patterns

# Pattern 1: Current with negative lookbehind
pattern1 = re.compile(r'(?<![-])\s*\$?\s*([\d,]+)(?:k|K)?\s*(?:per|/)?\s*(hour|hr|week|month|year|annual|annum)?', re.IGNORECASE)

# Pattern 2: Without lookbehind, just check
pattern2 = re.compile(r'\$?\s*([\d,]+)(?:k|K)?\s*(?:per|/)?\s*(hour|hr|week|month|year|annual|annum)?', re.IGNORECASE)

# This is what the test passes
text = "-$50,000 per year"
print(f'Text: {text}')

# This is what happens after the cleaning
cleaned = text.replace('\\$', '$').replace('\\-', '-').replace('\\.', '.')
print(f'Cleaned: {cleaned}')

match1 = pattern1.search(cleaned)
print(f'Pattern 1 match: {match1}')
if match1:
    print(f'  Groups: {match1.groups()}')
    idx = match1.start()
    char_before = cleaned[idx-1] if idx > 0 else None
    print(f'  Match start: {idx}, char before: {char_before}')

match2 = pattern2.search(cleaned)
print(f'\nPattern 2 match: {match2}')
if match2:
    print(f'  Groups: {match2.groups()}')
    idx2 = match2.start()
    char_before2 = cleaned[idx2-1] if idx2 > 0 else None
    print(f'  Match start: {idx2}, char before: {char_before2}')
