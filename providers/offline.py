"""
Fully offline provider using Google's libphonenumber data.
No API key or network required.
"""
import phonenumbers
from phonenumbers import carrier, geocoder, timezone as tz_module
from normalizer import ParsedNumber

LINE_TYPE_MAP = {
    phonenumbers.PhoneNumberType.MOBILE: "Mobile",
    phonenumbers.PhoneNumberType.FIXED_LINE: "Landline",
    phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE: "Landline or Mobile",
    phonenumbers.PhoneNumberType.TOLL_FREE: "Toll-Free",
    phonenumbers.PhoneNumberType.PREMIUM_RATE: "Premium Rate",
    phonenumbers.PhoneNumberType.VOIP: "VoIP",
    phonenumbers.PhoneNumberType.PAGER: "Pager",
    phonenumbers.PhoneNumberType.SHARED_COST: "Shared Cost",
    phonenumbers.PhoneNumberType.PERSONAL_NUMBER: "Personal Number",
    phonenumbers.PhoneNumberType.UNKNOWN: "Unknown",
}


def lookup(parsed: ParsedNumber) -> dict:
    phone_obj = phonenumbers.parse(parsed.e164)
    lang = "en"

    carrier_name = carrier.name_for_number(phone_obj, lang) or None
    geo = geocoder.description_for_number(phone_obj, lang) or None
    timezones = list(tz_module.time_zones_for_number(phone_obj)) or None
    line_type = LINE_TYPE_MAP.get(
        phonenumbers.number_type(phone_obj), "Unknown"
    )

    return {
        "source": "offline (libphonenumber)",
        "carrier": carrier_name,
        "location": geo,
        "line_type": line_type,
        "timezones": timezones,
        "country_code": f"+{parsed.country_code}",
        "region": parsed.region,
    }
