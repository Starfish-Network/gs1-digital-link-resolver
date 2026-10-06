"""Parse GS1 Digital Link URIs into their Application Identifier components.

A Digital Link URI carries its identifiers in the path: ``/01/09506000134352/10/ABC123``
is GTIN 09506000134352, lot ABC123. Parsing is what lets a resolver route on *what was
scanned* rather than on the request as a whole, so it is deliberately free of transport,
auth and storage concerns.

The URI may be served under any stem (``https://example.com/some/prefix/01/...``), so
parsing starts at the first segment that names a primary key rather than at the root.
"""

from collections.abc import Mapping
from urllib.parse import quote, unquote

from pydantic import BaseModel, Field

from gs1_digital_link.application_identifiers import (
    CHECK_DIGIT_AIS,
    FIXED_LENGTHS,
    GLN,
    GTIN,
    LOT,
    PGLN,
    SERIAL,
    SSCC,
    is_primary_key,
    normalise_ai,
    qualifiers_for,
)
from gs1_digital_link.check_digit import calculate_check_digit


class DigitalLinkError(ValueError):
    """Raised when a path cannot be read as a GS1 Digital Link URI."""


class DigitalLinkURI(BaseModel):
    primary_key: str
    primary_value: str
    qualifiers: dict[str, str] = Field(default_factory=dict)
    attributes: dict[str, str] = Field(default_factory=dict)

    @property
    def gtin(self) -> str | None:
        return self.primary_value if self.primary_key == GTIN else None

    @property
    def sscc(self) -> str | None:
        return self.primary_value if self.primary_key == SSCC else None

    @property
    def gln(self) -> str | None:
        return self.primary_value if self.primary_key in (GLN, PGLN) else None

    @property
    def lot(self) -> str | None:
        return self.qualifiers.get(LOT)

    @property
    def serial(self) -> str | None:
        return self.qualifiers.get(SERIAL)

    def canonical_path(self) -> str:
        """Render back to the canonical form: primary key, then qualifiers in standard order.

        Attributes are deliberately dropped; the standard carries them in the query string,
        and they never identify the item being resolved.
        """
        parts = [self.primary_key, quote(self.primary_value, safe="")]
        for ai in qualifiers_for(self.primary_key):
            value = self.qualifiers.get(ai)
            if value is not None:
                parts.extend([ai, quote(value, safe="")])
        return "/" + "/".join(parts)


def normalise_value(ai: str, value: str) -> str:
    """Zero-pad a short GTIN to 14 digits; leave everything else as given.

    GTIN-8/12/13 and GTIN-14 denote the same trade item, so padding here is what makes
    two spellings of one product compare equal downstream.
    """
    if ai == GTIN and value.isdigit() and len(value) < 14:
        return value.zfill(14)
    return value


def _validate(ai: str, value: str) -> None:
    expected_length = FIXED_LENGTHS.get(ai)
    if expected_length is not None:
        if not value.isdigit() or len(value) != expected_length:
            raise DigitalLinkError(f"AI {ai} requires {expected_length} digits, got {value!r}")
    if ai in CHECK_DIGIT_AIS and int(value[-1]) != calculate_check_digit(value[:-1]):
        raise DigitalLinkError(f"AI {ai} value {value!r} has an invalid check digit")


def _split_path(path: str) -> list[str]:
    return [unquote(segment) for segment in path.split("/") if segment]


def _find_primary_key(segments: list[str]) -> int:
    """Index of the first segment naming a primary key, skipping any stem before it."""
    for index, segment in enumerate(segments):
        ai = normalise_ai(segment)
        if ai is not None and is_primary_key(ai):
            return index
    raise DigitalLinkError("no GS1 primary key found in path")


def parse_digital_link(
    path: str,
    query: Mapping[str, str] | None = None,
    *,
    validate: bool = True,
) -> DigitalLinkURI:
    """Parse a Digital Link path (and optional query) into its components.

    Query parameters that name an AI become attributes; the rest (``linkType`` and any
    other control parameter) are ignored, since they say what the caller wants rather
    than what was scanned.
    """
    segments = _split_path(path)
    start = _find_primary_key(segments)

    primary_key = normalise_ai(segments[start])
    if primary_key is None:  # unreachable: _find_primary_key already resolved it
        raise DigitalLinkError("no GS1 primary key found in path")
    if start + 1 >= len(segments):
        raise DigitalLinkError(f"primary key {primary_key} has no value")

    primary_value = normalise_value(primary_key, segments[start + 1])
    if validate:
        _validate(primary_key, primary_value)

    qualifiers: dict[str, str] = {}
    attributes: dict[str, str] = {}
    allowed = qualifiers_for(primary_key)
    last_qualifier_index = -1

    remaining = segments[start + 2 :]
    if len(remaining) % 2:
        raise DigitalLinkError(f"trailing path segment {remaining[-1]!r} has no value")

    for raw_ai, raw_value in zip(remaining[::2], remaining[1::2], strict=True):
        ai = normalise_ai(raw_ai)
        if ai is None:
            raise DigitalLinkError(f"path segment {raw_ai!r} is not a GS1 application identifier")
        if ai in allowed:
            index = allowed.index(ai)
            # Order is load-bearing: /10/lot/21/serial and /21/serial/10/lot are not the
            # same URI, and only the first is valid.
            if index <= last_qualifier_index:
                raise DigitalLinkError(f"qualifier {ai} is out of order for primary key {primary_key}")
            last_qualifier_index = index
            if validate:
                _validate(ai, raw_value)
            qualifiers[ai] = raw_value
        else:
            attributes[ai] = raw_value

    for key, value in (query or {}).items():
        ai = normalise_ai(key)
        if ai is not None and ai not in qualifiers:
            attributes[ai] = value

    return DigitalLinkURI(
        primary_key=primary_key,
        primary_value=primary_value,
        qualifiers=qualifiers,
        attributes=attributes,
    )
