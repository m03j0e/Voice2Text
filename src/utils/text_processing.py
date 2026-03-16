import re

def remove_filler_words(text):
    if not text:
        return text

    cleaned = text

    # Remove filler words and any adjacent commas/spaces that would look awkward
    # E.g., "thinking, uh, about" -> "thinking about"
    # Match an optional comma, optional spaces, the filler word, an optional comma, and optional spaces
    # Replacing with a single space ensures we don't merge words.
    fillers = [r'\bum\b', r'\buh\b', r'\blike\b', r'\bso\b', r'\byou know\b']

    for filler in fillers:
        # Pattern: optional space + optional comma + optional space + filler + optional comma + optional space
        # We replace this whole awkward block with a single space
        pattern = r'\s*,?\s*' + filler + r'\s*,?\s*'
        cleaned = re.sub(pattern, ' ', cleaned, flags=re.IGNORECASE)

    # 2. Clean up any resulting double spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    # 3. Clean up hanging punctuation at the beginning
    cleaned = re.sub(r'^[,\s]+', '', cleaned)

    if cleaned and len(cleaned) > 0:
        cleaned = cleaned[0].upper() + cleaned[1:]

    return cleaned
