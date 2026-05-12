"""
FCC Consumer Broadband / phone data APIs — no API key required.
Uses the FCC's public Number Portability lookup to check if a number
has been ported (landline → mobile, etc.) and to confirm carrier.
"""
import httpx
from normalizer import ParsedNumber

# FCC public number portability check endpoint
FCC_LNP_URL = "https://data.fcc.gov/api/block/find"


def lookup(parsed: ParsedNumber) -> dict | None:
    if parsed.country_code != 1:
        return None

    national = parsed.national_number
    if len(national) < 10:
        return None

    npa = national[:3]
    nxx = national[3:6]
    line = national[6:10]

    try:
        resp = httpx.get(
            FCC_LNP_URL,
            params={
                "number": f"{npa}{nxx}{line}",
                "format": "json",
            },
            timeout=5,
        )
        if resp.status_code != 200:
            return None

        data = resp.json()
        block = data.get("Block", {})
        carrier_block = data.get("Carrier", {})

        if not block and not carrier_block:
            return None

        return {
            "source": "FCC",
            "fcc_carrier_name": carrier_block.get("name"),
            "fcc_carrier_id": carrier_block.get("id"),
            "rate_center": block.get("ratecenter"),
            "state": block.get("state"),
            "ocn": block.get("ocn"),  # Operating Company Number
        }
    except Exception:
        return None
