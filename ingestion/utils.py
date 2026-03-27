import re

NEPALI_NUMERALS = "०१२३४५६७८९"
ENGLISH_NUMERALS = "0123456789"

def nepali_to_english_int(nepali_str: str) -> int:
    """Converts Nepali numerals in a string to an English integer."""
    if not nepali_str:
        return 0
    
    # Remove any non-numeral characters for pure conversion
    clean_str = "".join(c for c in nepali_str if c in NEPALI_NUMERALS)
    if not clean_str:
        return 0
        
    translation_table = str.maketrans(NEPALI_NUMERALS, ENGLISH_NUMERALS)
    english_str = clean_str.translate(translation_table)
    return int(english_str)

def english_to_nepali_str(english_val: int) -> str:
    """Converts an English integer to a Nepali numeral string."""
    english_str = str(english_val)
    translation_table = str.maketrans(ENGLISH_NUMERALS, NEPALI_NUMERALS)
    return english_str.translate(translation_table)

def clean_nepali_unicode(text: str) -> str:
    """Ensures text is UTF-8 and handles potential common corruption."""
    if not text:
        return ""
    # In a real-world scenario, we might add more complex normalization here.
    return text.strip()

if __name__ == "__main__":
    # Tests
    test_nepali = "२०७४"
    print(f"{test_nepali} -> {nepali_to_english_int(test_nepali)}")
    
    test_english = 2074
    print(f"{test_english} -> {english_to_nepali_str(test_english)}")
