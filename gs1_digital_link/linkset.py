"""Turn a parsed GS1 Digital Link into a linkset.

Resolution is template substitution over the identifier that was scanned, which is what
makes two lots of the same product resolve to two different pages. Templates are supplied
by the host application, so nothing here knows about any particular back end.

A template whose placeholders the identifier cannot fill is skipped rather than rendered
with a blank: a lot-level link simply does not apply to a scan that carried no lot.
"""

import re
from collections.abc import Sequence
from urllib.parse import quote

from pydantic import BaseModel, Field

from gs1_digital_link.application_identifiers import (
    GLN,
    GTIN,
    LOT,
    PGLN,
    SERIAL,
    SSCC,
)
from gs1_digital_link.digital_link import DigitalLinkURI

LINK_TYPE_ALL = "all"

_PLACEHOLDER = re.compile(r"\{([^{}]+)\}")

_NAMED_COMPONENTS = {
    GTIN: "gtin",
    SSCC: "sscc",
    GLN: "gln",
    PGLN: "pgln",
    LOT: "lot",
    SERIAL: "serial",
}


class LinkTemplate(BaseModel):
    link_type: str
    href_template: str
    title: str | None = None
    media_type: str | None = None
    is_default: bool = False


class ResolvedLink(BaseModel):
    """Fields carry GS1's linkset key names, as ``GS1DigitalLinkResponse`` already does."""

    linkType: str  # noqa: N815
    href: str
    title: str | None = None
    type: str | None = None


class LinkSet(BaseModel):
    anchor: str
    links: list[ResolvedLink] = Field(default_factory=list)

    def default(self) -> ResolvedLink | None:
        return self.links[0] if self.links else None


def _components(uri: DigitalLinkURI) -> dict[str, str]:
    """Placeholder values a template may reference, by friendly name and by AI code."""
    values: dict[str, str] = {uri.primary_key: uri.primary_value}
    named = _NAMED_COMPONENTS.get(uri.primary_key)
    if named:
        values[named] = uri.primary_value

    for ai, value in uri.qualifiers.items():
        values[ai] = value
        named = _NAMED_COMPONENTS.get(ai)
        if named:
            values[named] = value

    for ai, value in uri.attributes.items():
        values.setdefault(ai, value)

    return values


def _placeholders(template: str) -> set[str]:
    return set(_PLACEHOLDER.findall(template))


def render(template: LinkTemplate, uri: DigitalLinkURI) -> str | None:
    """Render a template against an identifier, or None when it does not apply.

    Substitution is done directly rather than through ``str.format``, which reads an
    all-digit placeholder such as ``{400}`` as a positional index and so cannot address
    an AI by its code.
    """
    values = _components(uri)
    if not _placeholders(template.href_template) <= values.keys():
        return None
    return _PLACEHOLDER.sub(lambda match: quote(values[match.group(1)], safe=""), template.href_template)


def resolve_links(
    uri: DigitalLinkURI,
    templates: Sequence[LinkTemplate],
    *,
    link_type: str | None = None,
) -> LinkSet:
    """Build the linkset for an identifier, optionally narrowed to one link type.

    ``link_type`` of ``all`` (or None) returns every applicable link, defaults first, which
    is also the order a caller wanting a single redirect target should read.
    """
    applicable: list[tuple[LinkTemplate, str]] = []
    for template in templates:
        if link_type not in (None, LINK_TYPE_ALL) and template.link_type != link_type:
            continue
        href = render(template, uri)
        if href is not None:
            applicable.append((template, href))

    applicable.sort(key=lambda pair: not pair[0].is_default)

    return LinkSet(
        anchor=uri.canonical_path(),
        links=[
            ResolvedLink(
                linkType=template.link_type,
                href=href,
                title=template.title,
                type=template.media_type,
            )
            for template, href in applicable
        ],
    )


def link_header(linkset: LinkSet) -> str:
    """Serialise a linkset as an RFC 8288 ``Link`` header, which is how a 307 carries alternatives."""
    return ", ".join(
        f'<{link.href}>; rel="{link.linkType}"' + (f'; title="{link.title}"' if link.title else "")
        for link in linkset.links
    )
