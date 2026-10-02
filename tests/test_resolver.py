"""Route tests for the resolver.

Requests deliberately carry no credential: a resolver that needed one could not be
scanned off a package.
"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from gs1_digital_link.linkset import LinkSet, LinkTemplate
from gs1_digital_link.resolver import (
    DEFAULT_STEM,
    LINKSET_MEDIA_TYPE,
    WELL_KNOWN_PATH,
    build_resolver_router,
)

VALID_GTIN = "00000010092095"
LOT = "US20260611-A"
BASE_URL = "http://test"

TEMPLATES = [
    LinkTemplate(
        link_type="gs1:productInfo",
        href_template="https://app.example.com/p/{gtin}",
        title="Product information",
        media_type="text/html",
        is_default=True,
    ),
    LinkTemplate(
        link_type="gs1:traceability",
        href_template="https://app.example.com/trace/{gtin}/{lot}",
        title="Traceability",
        media_type="text/html",
    ),
    LinkTemplate(
        link_type="gs1:epcis",
        href_template="https://api.example.com/epcis",
        media_type="application/json",
    ),
]

app = FastAPI()
app.include_router(
    build_resolver_router(templates=TEMPLATES, resolver_base_url="https://id.example.com")
)


async def _get(path: str, headers: dict[str, str] | None = None):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=BASE_URL, follow_redirects=False
    ) as client:
        return await client.get(path, headers=headers)


@pytest.mark.asyncio
async def test_redirects_to_the_default_link_without_any_credential():
    response = await _get(f"{DEFAULT_STEM}/01/{VALID_GTIN}/10/{LOT}")

    assert response.status_code == 307
    assert response.headers["location"] == f"https://app.example.com/p/{VALID_GTIN}"


@pytest.mark.asyncio
async def test_redirect_carries_alternatives_in_the_link_header():
    response = await _get(f"{DEFAULT_STEM}/01/{VALID_GTIN}/10/{LOT}")

    assert 'rel="gs1:traceability"' in response.headers["link"]
    assert 'rel="gs1:epcis"' in response.headers["link"]


@pytest.mark.asyncio
async def test_link_type_all_returns_the_linkset():
    response = await _get(f"{DEFAULT_STEM}/01/{VALID_GTIN}/10/{LOT}?linkType=all")

    assert response.status_code == 200
    linkset = LinkSet(**response.json())
    assert linkset.anchor == f"/01/{VALID_GTIN}/10/{LOT}"
    assert {link.linkType for link in linkset.links} == {
        "gs1:productInfo",
        "gs1:traceability",
        "gs1:epcis",
    }


@pytest.mark.asyncio
async def test_linkset_media_type_is_honoured():
    response = await _get(
        f"{DEFAULT_STEM}/01/{VALID_GTIN}/10/{LOT}", {"accept": LINKSET_MEDIA_TYPE}
    )

    assert response.status_code == 200
    assert LinkSet(**response.json()).links


@pytest.mark.asyncio
async def test_narrowing_to_one_link_type_redirects_there():
    response = await _get(f"{DEFAULT_STEM}/01/{VALID_GTIN}/10/{LOT}?linkType=gs1:traceability")

    assert response.status_code == 307
    assert response.headers["location"].endswith(f"/trace/{VALID_GTIN}/{LOT}")


@pytest.mark.asyncio
async def test_different_lots_resolve_to_different_targets():
    first = await _get(f"{DEFAULT_STEM}/01/{VALID_GTIN}/10/LOT1?linkType=gs1:traceability")
    second = await _get(f"{DEFAULT_STEM}/01/{VALID_GTIN}/10/LOT2?linkType=gs1:traceability")

    assert first.headers["location"] != second.headers["location"]


@pytest.mark.asyncio
async def test_a_lot_level_link_is_not_offered_without_a_lot():
    response = await _get(f"{DEFAULT_STEM}/01/{VALID_GTIN}?linkType=gs1:traceability")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_an_invalid_check_digit_is_rejected():
    response = await _get(f"{DEFAULT_STEM}/01/00000010092094")

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_discovery_document_describes_the_resolver():
    response = await _get(WELL_KNOWN_PATH)

    assert response.status_code == 200
    body = response.json()
    assert body["resolverRoot"] == f"https://id.example.com{DEFAULT_STEM}"
    assert "01" in body["supportedPrimaryKeys"]
    assert "gs1:traceability" in body["supportedLinkTypes"]


@pytest.mark.asyncio
async def test_a_custom_stem_moves_the_resolver():
    custom = FastAPI()
    custom.include_router(
        build_resolver_router(
            templates=TEMPLATES, resolver_base_url="https://id.example.com", stem="/id"
        )
    )
    async with AsyncClient(
        transport=ASGITransport(app=custom), base_url=BASE_URL, follow_redirects=False
    ) as client:
        moved = await client.get(f"/id/01/{VALID_GTIN}/10/{LOT}")
        gone = await client.get(f"{DEFAULT_STEM}/01/{VALID_GTIN}/10/{LOT}")

    assert moved.status_code == 307
    assert gone.status_code == 404
