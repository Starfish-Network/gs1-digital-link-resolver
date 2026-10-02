"""GS1 Application Identifier reference data for Digital Link URIs.

Only the subset the Digital Link standard gives structural meaning to: which AIs may
open a URI path (primary keys), which may follow each one (qualifiers), and the
alphanumeric aliases GS1 permits in place of the numeric code. Everything else an AI
can appear as in a Digital Link is a data attribute, which needs no table.
"""

GTIN = "01"
SSCC = "00"
GDTI = "253"
GCN = "255"
GINC = "401"
GSIN = "402"
GLN = "414"
PGLN = "417"
GRAI = "8003"
GIAI = "8004"
ITIP = "8006"
CPID = "8010"
GMN = "8013"
GSRN_PROVIDER = "8017"
GSRN_RECIPIENT = "8018"

CPV = "22"
LOT = "10"
SERIAL = "21"
GLN_EXTENSION = "254"
CPID_SERIAL = "8011"
SRIN = "8019"

PRIMARY_KEY_QUALIFIERS: dict[str, tuple[str, ...]] = {
    GTIN: (CPV, LOT, SERIAL),
    ITIP: (CPV, LOT, SERIAL),
    SSCC: (),
    GDTI: (),
    GCN: (),
    GINC: (),
    GSIN: (),
    GLN: (GLN_EXTENSION,),
    PGLN: (),
    GRAI: (),
    GIAI: (),
    CPID: (CPID_SERIAL,),
    GMN: (),
    GSRN_PROVIDER: (SRIN,),
    GSRN_RECIPIENT: (SRIN,),
}
"""Qualifiers each primary key admits, in the order the standard requires them to appear.

A qualifier may be omitted, but those present must keep this relative order: /01/{gtin}/10/{lot}/21/{serial}
is valid and /01/{gtin}/21/{serial}/10/{lot} is not.
"""

SHORT_NAMES: dict[str, str] = {
    "gtin": GTIN,
    "sscc": SSCC,
    "gdti": GDTI,
    "gcn": GCN,
    "ginc": GINC,
    "gsin": GSIN,
    "gln": GLN,
    "party": PGLN,
    "grai": GRAI,
    "giai": GIAI,
    "itip": ITIP,
    "cpid": CPID,
    "gmn": GMN,
    "gsrnp": GSRN_PROVIDER,
    "gsrn": GSRN_RECIPIENT,
    "cpv": CPV,
    "lot": LOT,
    "ser": SERIAL,
    "glnx": GLN_EXTENSION,
    "cpsn": CPID_SERIAL,
    "srin": SRIN,
}

FIXED_LENGTHS: dict[str, int] = {
    SSCC: 18,
    GTIN: 14,
    GLN: 13,
    PGLN: 13,
    GSRN_PROVIDER: 18,
    GSRN_RECIPIENT: 18,
    "11": 6,
    "12": 6,
    "13": 6,
    "15": 6,
    "16": 6,
    "17": 6,
}
"""Digits required after normalisation, for the AIs this module validates."""

CHECK_DIGIT_AIS = frozenset({SSCC, GTIN, GLN, PGLN, GSRN_PROVIDER, GSRN_RECIPIENT})


def normalise_ai(segment: str) -> str | None:
    """Return the numeric AI for a path segment, accepting GS1's alphanumeric aliases.

    None when the segment is neither, which is how the parser tells an AI apart from a
    value that has drifted into an AI position.
    """
    if segment.isdigit():
        return segment
    return SHORT_NAMES.get(segment.lower())


def is_primary_key(ai: str) -> bool:
    return ai in PRIMARY_KEY_QUALIFIERS


def qualifiers_for(primary_key: str) -> tuple[str, ...]:
    return PRIMARY_KEY_QUALIFIERS.get(primary_key, ())
