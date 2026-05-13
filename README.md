# Phone Lookup

A free, privacy-focused reverse phone number lookup tool for the command line. Works fully offline for core data, and enriches results with free public APIs, web dork searches, and community spam databases — no paid services required.

---

## Features

- **Offline-first** — carrier, line type, region, and timezone data via Google's libphonenumber (no internet needed)
- **Web dork search** — runs targeted DuckDuckGo dork queries to surface business name, owner, and company context
- **Business directory hits** — direct structured scrapes of YellowPages and BBB for name, category, address, and rating
- **FCC lookup** — rate center, state, and carrier OCN via the FCC's public API (no key required)
- **NANPA area code data** — service area and state for US/Canada numbers
- **Spam reporting** — scrapes 800notes and WhoCalledMe for community spam reports and caller comments
- **Result caching** — SQLite cache with a 7-day TTL so repeated lookups are instant and free
- **Batch mode** — look up a whole CSV file of numbers at once
- **Multiple output formats** — rich terminal table, JSON, or CSV
- **Optional API keys** — plug in NumVerify or AbstractAPI for extra carrier detail (250 free lookups/month each)
- **US/Canada primary** — full enrichment for North American numbers, global parsing and offline data for international numbers

---

## Requirements

- Python 3.10+
- pip

---

## Installation

```bash
cd ~/Desktop/phone_lookup
pip install -r requirements.txt
```

---

## Usage

### Single number lookup
```bash
python cli.py 5551234567
python cli.py +1-555-123-4567
python cli.py "(555) 123-4567"
```

### International number
```bash
python cli.py +44 7911 123456
```

### Skip spam scraping (faster)
```bash
python cli.py 5551234567 --no-scrape
```

### Skip web dork search (fastest — carrier/line type only)
```bash
python cli.py 5551234567 --no-dork
python cli.py 5551234567 --no-scrape --no-dork
```

### JSON output
```bash
python cli.py 5551234567 --format json
```

### Batch lookup from a CSV file
Your CSV must have a column named `number`:
```csv
number
5551234567
8005551212
+14155552671
```
```bash
python cli.py --batch numbers.csv
python cli.py --batch numbers.csv --format csv > results.csv
```

### Clear the local cache
```bash
python cli.py --clear-cache
```

### All options
```
usage: phone_lookup [-h] [--batch FILE] [--format {table,json,csv}]
                    [--no-scrape] [--no-dork] [--no-cache] [--clear-cache]
                    [--region CC] [number ...]

positional arguments:
  number                Phone number(s) to look up (any common format)

options:
  --batch FILE          CSV file with a column named 'number' for bulk lookups
  --format              Output format: table (default), json, or csv
  --no-scrape           Skip public caller ID scraping (faster, no spam data)
  --no-dork             Skip web dork search (faster, no name/company data)
  --no-cache            Ignore and do not write the local cache
  --clear-cache         Clear all cached results and exit
  --region CC           Default region for numbers without a country code (default: US)
```

---

## Data Sources

| Source | Data provided | Cost | Requires key |
|---|---|---|---|
| Google libphonenumber | Carrier, line type, region, timezone | Free | No |
| DuckDuckGo dork search | Business/owner name, company context | Free | No |
| YellowPages (direct scrape) | Business name, category, address | Free | No |
| BBB (direct scrape) | Business name, BBB letter rating | Free | No |
| FCC public API | Rate center, state, carrier OCN | Free | No |
| NANPA API | Area code service area, state | Free | No |
| 800notes (scrape) | Spam reports, user comments | Free | No |
| WhoCalledMe (scrape) | Spam reports, caller type label | Free | No |
| NumVerify | Carrier, line type, country | 250/month free | Optional |
| AbstractAPI | Carrier, line type, country | 250/month free | Optional |

### Web Dork Queries

The dork search provider runs four targeted queries per lookup:

| Query | Purpose |
|---|---|
| `"555-123-4567" OR "(555) 123-4567"` | Any page that lists the number |
| `"555-123-4567" site:yellowpages.com OR site:yelp.com OR site:bbb.org` | Business directories only |
| `"555-123-4567" owner OR "contact us" OR company OR LLC OR Inc` | Owner and contact context signals |
| `"555-123-4567" site:linkedin.com` | LinkedIn business and person profiles |

Results are filtered to remove known reverse-lookup aggregator sites (Whitepages, Spokeo, etc.) so only genuine source pages surface as name candidates.

---

## Optional API Keys

The script works fully without any API keys. If you want extra carrier detail from NumVerify or AbstractAPI:

1. Copy `.env.example` to `.env`
2. Fill in any keys you have

```bash
cp .env.example .env
```

```env
NUMVERIFY_API_KEY=your_key_here
ABSTRACTAPI_KEY=your_key_here
```

Sign-up links (both have free tiers):
- NumVerify: https://numverify.com/
- AbstractAPI: https://www.abstractapi.com/phone-validation-api

---

## Project Structure

```
phone_lookup/
├── cli.py                  Entry point — all CLI arguments handled here
├── normalizer.py           Parses any phone format to E.164
├── aggregator.py           Runs all providers and merges results
├── cache.py                SQLite result cache (~/.cache/phone_lookup/)
├── formatter.py            Rich table, JSON, and CSV output
├── requirements.txt
├── .env.example            Template for optional API keys
└── providers/
    ├── offline.py          phonenumbers lib (always runs, no network)
    ├── dork_search.py      DuckDuckGo dork queries + YellowPages/BBB scrapes
    ├── fcc.py              FCC public REST API
    ├── nanpa.py            NANPA area code API
    ├── scraper.py          800notes + WhoCalledMe scraper
    └── optional_apis.py    NumVerify / AbstractAPI (key required)
```

---

## Cache

Lookup results are cached locally in `~/.cache/phone_lookup/cache.db` (SQLite) with a 7-day TTL. This means:
- Repeat lookups of the same number are instant and use no network
- The cache is keyed by E.164 format so `555-123-4567` and `(555) 123 4567` share the same entry

To bypass the cache for a single lookup: `--no-cache`
To wipe all cached results: `--clear-cache`

---

## Notes

- **Web dork search** runs 4 DuckDuckGo queries plus direct YellowPages and BBB scrapes. This adds ~5–8 seconds per lookup. Use `--no-dork` to skip it when you only need carrier/line type data.
- **Spam scraping** (800notes, WhoCalledMe) adds ~2 seconds per lookup due to polite rate limiting. Use `--no-scrape` to skip.
- Combining `--no-dork --no-scrape` gives the fastest possible result using only offline and free API data.
- **Name/company accuracy** — dork results are heuristic. The tool filters out known aggregator sites and ranks YellowPages/BBB structured hits highest, but results are not guaranteed for private individuals.
- **International numbers** outside North America receive offline data only (carrier, type, region, timezone). FCC, NANPA, dork search, and scraper providers are US/Canada only.
- This tool is intended for personal, informational use. Respect the terms of service of any sites you query.
