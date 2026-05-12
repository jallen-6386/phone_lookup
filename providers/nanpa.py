"""
NANPA (North American Numbering Plan) prefix lookup.
Downloads the public bulk CSV from nanpa.com on first use and caches it locally.
Only applies to US/Canada numbers (country code +1).
"""
import csv
import os
import httpx
from pathlib import Path
from normalizer import ParsedNumber

NANPA_URL = "https://www.nanpa.com/reports/reports_cocodes_assign.zip"
CACHE_DIR = Path.home() / ".cache" / "phone_lookup"
CSV_PATH = CACHE_DIR / "nanpa_cocodes.csv"

# Fallback: derive NPA (area code) info from the national number directly
# Full NANPA bulk download requires account; use the public area code API instead.
NANPA_AREA_CODE_API = "https://api.nanpa.com/reports/areaCodeInfo/{npa}"


def _npa_from_parsed(parsed: ParsedNumber) -> str | None:
    """Extract the 3-digit NPA (area code) from a +1 number."""
    if parsed.country_code != 1:
        return None
    national = parsed.national_number
    if len(national) >= 10:
        return national[:3]
    return None


def lookup(parsed: ParsedNumber) -> dict | None:
    if parsed.country_code != 1:
        return None

    npa = _npa_from_parsed(parsed)
    if not npa:
        return None

    try:
        resp = httpx.get(
            f"https://api.nanpa.com/reports/areaCodeInfo/{npa}",
            timeout=5,
            follow_redirects=True,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        # The API returns a list; grab the first entry
        entries = data if isinstance(data, list) else data.get("areaCodeInfoList", [])
        if not entries:
            return None
        entry = entries[0]
        return {
            "source": "NANPA",
            "npa": npa,
            "state_province": entry.get("assignedToState") or entry.get("state"),
            "service_area": entry.get("geographicName") or entry.get("areaCodeCity"),
            "in_service": entry.get("inServiceDate"),
            "npa_type": entry.get("npaType"),
        }
    except Exception:
        return None
