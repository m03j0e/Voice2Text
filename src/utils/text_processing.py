import re

def remove_filler_words(text):
    fillers = [r'\bum\b', r'\buh\b', r'\blike\b', r'\bso\b', r'\byou know\b']
    cleaned = text
    for filler in fillers:
        cleaned = re.sub(filler, '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned
