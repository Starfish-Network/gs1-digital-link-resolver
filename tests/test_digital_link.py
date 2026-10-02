import pytest

from gs1_digital_link.application_identifiers import GLN, GTIN, LOT, SERIAL, SSCC
from gs1_digital_link.digital_link import (
    DigitalLinkError,
    parse_digital_link,
)

VALID_GTIN = "00000010092095"
VALID_SSCC = "106141411234567897"
VALID_GLN = "0614141000012"


def test_parses_gtin_and_lot():
    uri = parse_digital_link(f"/01/{VALID_GTIN}/10/US20260611-A")

    assert uri.primary_key == GTIN
    assert uri.gtin == VALID_GTIN
    assert uri.lot == "US20260611-A"
    assert uri.serial is None


def test_parses_gtin_lot_and_serial():
    uri = parse_digital_link(f"/01/{VALID_GTIN}/10/LOT1/21/SER9")

    assert uri.qualifiers == {LOT: "LOT1", SERIAL: "SER9"}


def test_accepts_alphanumeric_short_names():
    uri = parse_digital_link(f"/gtin/{VALID_GTIN}/lot/LOT1/ser/SER9")

    assert uri.primary_key == GTIN
    assert uri.lot == "LOT1"
    assert uri.serial == "SER9"


def test_ignores_a_stem_before_the_primary_key():
    uri = parse_digital_link(f"/some/hosted/prefix/01/{VALID_GTIN}/10/LOT1")

    assert uri.gtin == VALID_GTIN
    assert uri.lot == "LOT1"


def test_pads_short_gtin_to_fourteen_digits():
    # GTIN-12 and GTIN-14 denote the same trade item.
    uri = parse_digital_link("/01/614141000036")

    assert uri.gtin == "00614141000036"


def test_parses_sscc():
    uri = parse_digital_link(f"/00/{VALID_SSCC}")

    assert uri.primary_key == SSCC
    assert uri.sscc == VALID_SSCC


def test_parses_gln_with_extension():
    uri = parse_digital_link(f"/414/{VALID_GLN}/254/32a%2Fb")

    assert uri.primary_key == GLN
    assert uri.gln == VALID_GLN
    assert uri.qualifiers["254"] == "32a/b"


def test_non_qualifier_path_ais_become_attributes():
    uri = parse_digital_link(f"/01/{VALID_GTIN}/10/LOT1/17/260611")

    assert uri.qualifiers == {LOT: "LOT1"}
    assert uri.attributes == {"17": "260611"}


def test_query_ais_become_attributes_and_control_params_are_ignored():
    uri = parse_digital_link(
        f"/01/{VALID_GTIN}",
        {"400": "PO43706", "linkType": "gs1:epcis", "00": "1234567890654321"},
    )

    assert uri.attributes == {"400": "PO43706", "00": "1234567890654321"}


def test_canonical_path_round_trips_and_drops_attributes():
    uri = parse_digital_link(f"/prefix/gtin/{VALID_GTIN}/lot/LOT1/17/260611")

    assert uri.canonical_path() == f"/01/{VALID_GTIN}/10/LOT1"


def test_canonical_path_percent_encodes_values():
    uri = parse_digital_link(f"/01/{VALID_GTIN}/10/A%2FB")

    assert uri.canonical_path() == f"/01/{VALID_GTIN}/10/A%2FB"


def test_rejects_an_invalid_check_digit():
    with pytest.raises(DigitalLinkError, match="check digit"):
        parse_digital_link("/01/00000010092094")


def test_rejects_qualifiers_in_the_wrong_order():
    with pytest.raises(DigitalLinkError, match="out of order"):
        parse_digital_link(f"/01/{VALID_GTIN}/21/SER9/10/LOT1")


def test_rejects_a_trailing_segment_with_no_value():
    with pytest.raises(DigitalLinkError, match="no value"):
        parse_digital_link(f"/01/{VALID_GTIN}/10")


def test_rejects_a_primary_key_with_no_value():
    with pytest.raises(DigitalLinkError, match="no value"):
        parse_digital_link("/01")


def test_rejects_a_path_with_no_primary_key():
    with pytest.raises(DigitalLinkError, match="no GS1 primary key"):
        parse_digital_link("/products/some-sku")


def test_rejects_a_non_identifier_in_an_ai_position():
    with pytest.raises(DigitalLinkError, match="not a GS1 application identifier"):
        parse_digital_link(f"/01/{VALID_GTIN}/colour/red")


def test_validation_can_be_switched_off():
    uri = parse_digital_link("/01/00000010092094", validate=False)

    assert uri.gtin == "00000010092094"


def test_parses_the_deltatrak_berry_link():
    """The URL circulated as the berry demo, so the parser must agree with a live code."""
    uri = parse_digital_link(
        f"/01/{VALID_GTIN}/10/US20260611-A",
        {"00": "1234567890654321", "400": "PO43706"},
    )

    assert uri.gtin == VALID_GTIN
    assert uri.lot == "US20260611-A"
    assert uri.attributes == {"00": "1234567890654321", "400": "PO43706"}
