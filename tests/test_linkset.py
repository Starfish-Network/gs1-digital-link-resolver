from gs1_digital_link.digital_link import parse_digital_link
from gs1_digital_link.linkset import (
    LinkTemplate,
    link_header,
    render,
    resolve_links,
)

VALID_GTIN = "00000010092095"

TRACE = LinkTemplate(
    link_type="gs1:traceability",
    href_template="https://id.example.com/trace/{gtin}/{lot}",
    title="Trace",
)
PRODUCT = LinkTemplate(
    link_type="gs1:productInfo",
    href_template="https://id.example.com/product/{gtin}",
    title="Product",
    is_default=True,
)
EPCIS = LinkTemplate(
    link_type="gs1:epcis",
    href_template="https://api.example.com/epcis?gtin={gtin}",
)


def test_resolves_different_lots_to_different_links():
    first = resolve_links(parse_digital_link(f"/01/{VALID_GTIN}/10/LOT1"), [TRACE])
    second = resolve_links(parse_digital_link(f"/01/{VALID_GTIN}/10/LOT2"), [TRACE])

    assert first.links[0].href.endswith("/LOT1")
    assert second.links[0].href.endswith("/LOT2")


def test_skips_a_template_the_identifier_cannot_fill():
    linkset = resolve_links(parse_digital_link(f"/01/{VALID_GTIN}"), [TRACE, PRODUCT])

    assert [link.linkType for link in linkset.links] == ["gs1:productInfo"]


def test_narrowing_to_one_link_type():
    uri = parse_digital_link(f"/01/{VALID_GTIN}/10/LOT1")

    linkset = resolve_links(uri, [TRACE, PRODUCT, EPCIS], link_type="gs1:epcis")

    assert [link.linkType for link in linkset.links] == ["gs1:epcis"]


def test_all_returns_every_applicable_link_with_the_default_first():
    uri = parse_digital_link(f"/01/{VALID_GTIN}/10/LOT1")

    linkset = resolve_links(uri, [TRACE, PRODUCT, EPCIS], link_type="all")

    assert [link.linkType for link in linkset.links] == [
        "gs1:productInfo",
        "gs1:traceability",
        "gs1:epcis",
    ]
    default = linkset.default()
    assert default is not None
    assert default.linkType == "gs1:productInfo"


def test_anchor_is_the_canonical_identifier():
    uri = parse_digital_link(f"/stem/gtin/{VALID_GTIN}/lot/LOT1/17/260611")

    linkset = resolve_links(uri, [TRACE])

    assert linkset.anchor == f"/01/{VALID_GTIN}/10/LOT1"


def test_templates_may_reference_raw_ai_codes():
    template = LinkTemplate(link_type="gs1:pip", href_template="https://x.example.com/{01}/{10}")
    uri = parse_digital_link(f"/01/{VALID_GTIN}/10/LOT1")

    assert render(template, uri) == f"https://x.example.com/{VALID_GTIN}/LOT1"


def test_attributes_are_available_to_templates():
    template = LinkTemplate(link_type="gs1:pip", href_template="https://x.example.com/po/{400}")
    uri = parse_digital_link(f"/01/{VALID_GTIN}", {"400": "PO43706"})

    assert render(template, uri) == "https://x.example.com/po/PO43706"


def test_link_header_serialisation():
    uri = parse_digital_link(f"/01/{VALID_GTIN}/10/LOT1")

    header = link_header(resolve_links(uri, [PRODUCT, TRACE]))

    assert header == (
        f'<https://id.example.com/product/{VALID_GTIN}>; rel="gs1:productInfo"; title="Product", '
        f'<https://id.example.com/trace/{VALID_GTIN}/LOT1>; rel="gs1:traceability"; title="Trace"'
    )


def test_empty_linkset_has_no_default():
    linkset = resolve_links(parse_digital_link(f"/01/{VALID_GTIN}"), [TRACE])

    assert linkset.links == []
    assert linkset.default() is None
