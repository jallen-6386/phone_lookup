"""
Runs all providers and merges their results into a single flat dict.
Provider results are merged left-to-right; earlier (more authoritative)
values are not overwritten by later ones unless the earlier value is None.
"""
from normalizer import ParsedNumber
from providers import offline, nanpa, fcc, scraper, optional_apis


def run(parsed: ParsedNumber, no_scrape: bool = False) -> dict:
    result: dict = {
        "number": {
            "e164": parsed.e164,
            "national": parsed.national,
            "international": parsed.international,
            "valid": parsed.is_valid,
            "possible": parsed.is_possible,
        }
    }

    # Always run offline first — fastest, no network
    offline_data = offline.lookup(parsed)
    result["offline"] = offline_data

    # US/CA enrichment
    if parsed.country_code == 1:
        result["nanpa"] = nanpa.lookup(parsed)
        result["fcc"] = fcc.lookup(parsed)
        if not no_scrape:
            result["spam"] = scraper.lookup(parsed)

    # Optional paid-tier APIs (only populate if keys are configured)
    optional = optional_apis.lookup(parsed)
    if optional:
        result["optional_apis"] = optional

    # Build a flat "summary" from the best available data
    result["summary"] = _build_summary(result)
    return result


def _first(*values):
    for v in values:
        if v:
            return v
    return None


def _build_summary(r: dict) -> dict:
    offline = r.get("offline") or {}
    fcc_data = r.get("fcc") or {}
    nanpa_data = r.get("nanpa") or {}
    spam_data = r.get("spam") or {}
    opt = r.get("optional_apis") or {}
    opt_first = next(iter(opt.values()), {}) if opt else {}

    carrier = _first(
        opt_first.get("carrier"),
        offline.get("carrier"),
        fcc_data.get("fcc_carrier_name"),
    )
    line_type = _first(
        opt_first.get("line_type"),
        offline.get("line_type"),
    )
    location = _first(
        offline.get("location"),
        fcc_data.get("rate_center"),
        nanpa_data.get("service_area") if nanpa_data else None,
    )
    state = _first(
        fcc_data.get("state"),
        nanpa_data.get("state_province") if nanpa_data else None,
    )
    timezones = offline.get("timezones")
    spam_reports = spam_data.get("total_spam_reports")
    spam_labels = spam_data.get("spam_labels")

    return {
        "carrier": carrier,
        "line_type": line_type,
        "location": location,
        "state": state,
        "region": offline.get("region"),
        "timezones": timezones,
        "spam_reports": spam_reports,
        "spam_labels": spam_labels,
    }
