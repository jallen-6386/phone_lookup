"""
Web search provider using Google Dork-style queries via DuckDuckGo.
Extracts business/owner name context from search results and directly
scrapes YellowPages phone lookup for structured business data.

Dork strategies used:
  1. Exact number variants — catches any page that lists the number
  2. Business directory focus — site: operators on YP, Yelp, BBB
  3. Owner/contact context — keyword signals near the number
  4. LinkedIn company hit — surfaces business profiles
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
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

DDG_URL = "https://html.duckduckgo.com/html/"

# Domains that are themselves reverse-lookup aggregators — skip their titles
_LOOKUP_SITES = {
    "whitepages.com", "spokeo.com", "intelius.com", "beenverified.com",
    "truepeoplesearch.com", "anywho.com", "800notes.com", "whocalledme.com",
    "callerinfo.com", "calleridtest.com", "findwho.com", "numberguru.com",
}


def _variants(parsed: ParsedNumber) -> dict:
    n = parsed.national_number
    if len(n) == 10:
        npa, nxx, line = n[:3], n[3:6], n[6:]
        return {
            "dashes":  f"{npa}-{nxx}-{line}",
            "dots":    f"{npa}.{nxx}.{line}",
            "parens":  f"({npa}) {nxx}-{line}",
            "plain":   n,
        }
    return {"plain": n}


def _ddg(query: str, max_results: int = 6) -> list[dict]:
    try:
        resp = httpx.post(
            DDG_URL,
            data={"q": query, "kl": "us-en"},
            headers=HEADERS,
            timeout=10,
            follow_redirects=True,
        )
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        out = []
        for tag in soup.select(".result")[:max_results]:
            title   = (tag.select_one(".result__title")   or tag.select_one("h2"))
            snippet = tag.select_one(".result__snippet")
            url     = tag.select_one(".result__url")

            title_text   = title.get_text(strip=True)   if title   else ""
            snippet_text = snippet.get_text(strip=True) if snippet else ""
            url_text     = url.get_text(strip=True)     if url     else ""

            if title_text or snippet_text:
                out.append({"title": title_text, "url": url_text, "snippet": snippet_text})
        return out
    except Exception:
        return []


def _scrape_yellowpages(variants: dict) -> dict | None:
    dashes = variants.get("dashes")
    if not dashes:
        return None
    url = f"https://www.yellowpages.com/phone/{dashes}"
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=8, follow_redirects=True)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")

        name     = soup.select_one(".business-name, h1.n, .listing-name")
        category = soup.select_one(".categories a, .cat")
        address  = soup.select_one(".adr, .street-address, .address")
        website  = soup.select_one("a.track-visit-website, a[data-listing-id]")

        result = {
            "name":     name.get_text(strip=True)     if name     else None,
            "category": category.get_text(strip=True) if category else None,
            "address":  address.get_text(strip=True)  if address  else None,
            "website":  website.get("href")           if website  else None,
        }
        return result if result["name"] else None
    except Exception:
        return None


def _scrape_bbb(variants: dict) -> dict | None:
    dashes = variants.get("dashes")
    if not dashes:
        return None
    url = f"https://www.bbb.org/search?find_text={dashes}&find_loc="
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=8, follow_redirects=True)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")

        name_tag   = soup.select_one(".MuiTypography-h3, .result-business-name")
        rating_tag = soup.select_one(".bds-rating-module, .letter-grade")

        name   = name_tag.get_text(strip=True)   if name_tag   else None
        rating = rating_tag.get_text(strip=True) if rating_tag else None

        return {"name": name, "bbb_rating": rating} if name else None
    except Exception:
        return None


def _extract_names(results: list[dict], variants: dict) -> list[str]:
    number_strings = set(variants.values())
    skip_fragments = {
        "phone", "number", "lookup", "reverse", "search", "call", "caller",
        "find", "who", "called", "results", "free", "report",
    }

    candidates = []
    for r in results:
        raw_title = r.get("title", "")
        url = r.get("url", "")
        domain = re.sub(r"^www\.", "", url.split("/")[0]) if "/" in url else url

        # Skip titles from pure lookup aggregator sites
        if any(ls in domain for ls in _LOOKUP_SITES):
            continue

        # Strip trailing "| SiteName" or "- SiteName" suffixes
        title = re.split(r"\s[|\-–—]\s", raw_title)[0].strip()

        if not title or len(title) < 3:
            continue
        if any(num in title for num in number_strings):
            continue

        lower = title.lower()
        if sum(1 for w in skip_fragments if w in lower) >= 2:
            continue

        candidates.append(title)

    # Deduplicate preserving order
    seen: set[str] = set()
    unique = []
    for c in candidates:
        if c.lower() not in seen:
            seen.add(c.lower())
            unique.append(c)

    return unique[:5]


def _domain(url: str) -> str:
    url = re.sub(r"^https?://", "", url)
    return re.sub(r"^www\.", "", url.split("/")[0])


def lookup(parsed: ParsedNumber) -> dict | None:
    if parsed.country_code != 1:
        return None

    v = _variants(parsed)
    dashes = v.get("dashes", parsed.national_number)
    parens = v.get("parens", "")

    all_results: list[dict] = []

    # Dork 1 — exact number, most common formats
    all_results += _ddg(f'"{dashes}" OR "{parens}"')
    time.sleep(1)

    # Dork 2 — business directory sites only
    all_results += _ddg(
        f'"{dashes}" (site:yellowpages.com OR site:yelp.com OR site:bbb.org OR site:chamberofcommerce.com)'
    )
    time.sleep(1)

    # Dork 3 — owner / contact context signals
    all_results += _ddg(f'"{dashes}" (owner OR "contact us" OR company OR business OR LLC OR Inc)')
    time.sleep(1)

    # Dork 4 — LinkedIn company/person hit
    all_results += _ddg(f'"{dashes}" site:linkedin.com')
    time.sleep(1)

    # Direct structured hits
    yp  = _scrape_yellowpages(v)
    bbb = _scrape_bbb(v)
    time.sleep(1)

    # Collect unique source domains from DDG results
    found_on: list[str] = []
    for r in all_results:
        d = _domain(r.get("url", ""))
        if d and d not in found_on:
            found_on.append(d)

    possible_names = _extract_names(all_results, v)

    # Prefer structured hits at the top
    for structured_name in [
        bbb.get("name") if bbb else None,
        yp.get("name")  if yp  else None,
    ]:
        if structured_name and structured_name not in possible_names:
            possible_names.insert(0, structured_name)

    if not possible_names and not found_on and not yp and not bbb:
        return None

    return {
        "source":         "web dork (DuckDuckGo)",
        "possible_names": possible_names or None,
        "yellowpages":    yp,
        "bbb":            bbb,
        "found_on":       found_on[:10] or None,
        "raw_results":    all_results[:8],
    }
