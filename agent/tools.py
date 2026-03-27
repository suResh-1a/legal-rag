import re
from datetime import datetime, timedelta

def bs_to_ad(bs_date_str: str) -> str:
    """
    Simulated BS to AD conversion. 
    In a production system, use a library like `nepali-datetime`.
    Approximate rule: BS Year - 56.7 = AD Year.
    """
    # Look for year in BS (e.g., 2075)
    match = re.search(r"(\d{4})", bs_date_str)
    if not match:
        return "Unknown Date"
        
    # Convert Nepali digits if present
    from ingestion.utils import nepali_to_english_int
    bs_year = nepali_to_english_int(match.group(1))
    
    ad_year = bs_year - 57
    return f"{ad_year} AD (Approximate)"

def check_hada_myad(incident_date_bs: str, statute_limit_years: int) -> str:
    """
    Checks if a case is within the statute of limitations.
    """
    ad_date_approx = bs_to_ad(incident_date_bs)
    return f"Incident Date: {incident_date_bs} ({ad_date_approx}). Statute of Limitations: {statute_limit_years} years."

if __name__ == "__main__":
    print(bs_to_ad("२०७५-०१-०१"))
