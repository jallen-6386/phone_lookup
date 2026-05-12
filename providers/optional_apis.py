"""
Optional API providers — only active if keys are present in .env.
Copy .env.example to .env and fill in any keys you have.
The script works fully without these.
"""
import os
import httpx
from dotenv import load_dotenv
from normalizer import ParsedNumber

load_dotenv()


def _numverify(parsed: ParsedNumber) -> dict | None:
    key = os.getenv("NUMVERIFY_API_KEY")
    if not key:
        return None
    try:
        resp = httpx.get(
            "http://apilayer.net/api/validate",
            params={
                "access_key": key,
                "number": parsed.e164,
                "format": 1,
            },
            timeout=6,
        )
        data = resp.json()
        if not data.get("valid"):
            return None
        return {
            "source": "NumVerify",
            "carrier": data.get("carrier"),
            "line_type": data.get("line_type"),
            "location": data.get("location"),
            "country_name": data.get("country_name"),
        }
    except Exception:
        return None


def _abstractapi(parsed: ParsedNumber) -> dict | None:
    key = os.getenv("ABSTRACTAPI_KEY")
    if not key:
        return None
    try:
        resp = httpx.get(
            "https://phonevalidation.abstractapi.com/v1/",
            params={"api_key": key, "phone": parsed.e164},
            timeout=6,
        )
        data = resp.json()
        if not data.get("valid"):
            return None
        carrier_info = data.get("carrier", "")
        return {
            "source": "AbstractAPI",
            "carrier": carrier_info if isinstance(carrier_info, str) else carrier_info.get("name"),
            "line_type": data.get("type"),
            "country": data.get("country", {}).get("name"),
        }
    except Exception:
        return None


def lookup(parsed: ParsedNumber) -> dict | None:
    results = {}
    nv = _numverify(parsed)
    if nv:
        results["numverify"] = nv
    ab = _abstractapi(parsed)
    if ab:
        results["abstractapi"] = ab
    return results if results else None
