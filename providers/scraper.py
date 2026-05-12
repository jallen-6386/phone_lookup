"""
Scrapes publicly visible caller ID / spam report sites.
All data shown is already public. Rate-limits politely with a 1s delay.
"""
import time
import re
import httpx
from bs4 import BeautifulSoup
from normalizer import ParsedNumber

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}


def _digits_only(parsed: ParsedNumber) -> str:
    return parsed.national_number  # 10 digits, no formatting


def _scrape_800notes(national_digits: str) -> dict | None:
    """800notes.com — shows spam reports and user comments for US numbers."""
    npa = national_digits[:3]
    nxx = national_digits[3:6]
    line = national_digits[6:]
    url = f"https://800notes.com/Phone.aspx/{npa}-{nxx}-{line}"
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=8, follow_redirects=True)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")

        # Rating / vote summary
        rating_tag = soup.select_one(".rate-name")
        rating = rating_tag.get_text(strip=True) if rating_tag else None

        # Number of comments
        count_tag = soup.select_one(".cmt-count")
        comment_count = None
        if count_tag:
            m = re.search(r"\d+", count_tag.get_text())
            comment_count = int(m.group()) if m else None

        # Grab up to 3 most recent comment snippets
        comment_tags = soup.select(".ms-txt")[:3]
        comments = [c.get_text(strip=True) for c in comment_tags if c.get_text(strip=True)]

        if not rating and comment_count is None:
            return None

        return {
            "source": "800notes",
            "spam_rating": rating,
            "report_count": comment_count,
            "recent_comments": comments or None,
        }
    except Exception:
        return None


def _scrape_whocalledme(national_digits: str) -> dict | None:
    """WhoCalledMe — community spam reporting."""
    npa = national_digits[:3]
    nxx = national_digits[3:6]
    line = national_digits[6:]
    url = f"https://whocalledme.com/PhoneNumber/{npa}{nxx}{line}"
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=8, follow_redirects=True)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")

        # Overall caller type label
        label_tag = soup.select_one(".callerType") or soup.select_one(".caller-type")
        caller_type = label_tag.get_text(strip=True) if label_tag else None

        # Report count
        count_tag = soup.select_one(".numReports") or soup.select_one(".report-count")
        report_count = None
        if count_tag:
            m = re.search(r"\d+", count_tag.get_text())
            report_count = int(m.group()) if m else None

        if not caller_type and report_count is None:
            return None

        return {
            "source": "WhoCalledMe",
            "caller_type": caller_type,
            "report_count": report_count,
        }
    except Exception:
        return None


def lookup(parsed: ParsedNumber) -> dict | None:
    if parsed.country_code != 1:
        return None

    digits = _digits_only(parsed)
    if len(digits) < 10:
        return None

    results = {}

    notes = _scrape_800notes(digits)
    if notes:
        results["800notes"] = notes

    time.sleep(1)  # polite rate limit between sites

    wcm = _scrape_whocalledme(digits)
    if wcm:
        results["whocalledme"] = wcm

    if not results:
        return None

    # Aggregate spam signal
    report_counts = [
        v.get("report_count") for v in results.values() if v.get("report_count")
    ]
    total_reports = sum(report_counts) if report_counts else None

    ratings = [v.get("spam_rating") or v.get("caller_type") for v in results.values()]
    ratings = [r for r in ratings if r]

    return {
        "source": "public scrape",
        "total_spam_reports": total_reports,
        "spam_labels": ratings or None,
        "details": results,
    }
