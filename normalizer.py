import phonenumbers
from dataclasses import dataclass
from typing import Optional


@dataclass
class ParsedNumber:
    raw: str
    e164: str
    national: str
    international: str
    country_code: int
    national_number: str
    region: str  # ISO 3166-1 alpha-2, e.g. "US"
    is_valid: bool
    is_possible: bool


def parse(raw: str, default_region: str = "US") -> Optional[ParsedNumber]:
    try:
        parsed = phonenumbers.parse(raw, default_region)
    except phonenumbers.NumberParseException:
        return None

    region = phonenumbers.region_code_for_number(parsed) or default_region

    return ParsedNumber(
        raw=raw,
        e164=phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164),
        national=phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL),
        international=phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
        country_code=parsed.country_code,
        national_number=str(parsed.national_number),
        region=region,
        is_valid=phonenumbers.is_valid_number(parsed),
        is_possible=phonenumbers.is_possible_number(parsed),
    )
