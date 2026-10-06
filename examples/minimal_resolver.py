"""A complete resolver you can run.

    pip install -e ".[example]"
    uvicorn examples.minimal_resolver:app --reload

Follow a scan. The default link here is product-level, so it carries no lot:

    curl -i "http://127.0.0.1:8000/dl/01/09506000134352/10/ABC123"

Ask for the lot-level link and change the lot, to watch resolution follow the identifier:

    curl -i "http://127.0.0.1:8000/dl/01/09506000134352/10/ABC123?linkType=gs1:traceability"
    curl -i "http://127.0.0.1:8000/dl/01/09506000134352/10/XYZ789?linkType=gs1:traceability"

Ask for everything the identifier resolves to:

    curl "http://127.0.0.1:8000/dl/01/09506000134352/10/ABC123?linkType=all"

Read the discovery document:

    curl "http://127.0.0.1:8000/.well-known/gs1resolver"

And watch a mistyped identifier fail rather than redirect somewhere plausible:

    curl -i "http://127.0.0.1:8000/dl/01/09506000134353"
"""

from fastapi import FastAPI

from gs1_digital_link import LinkTemplate, build_resolver_router

TEMPLATES = [
    # The default is what an ordinary scan follows, so it is the one anybody may see.
    LinkTemplate(
        link_type="gs1:productInfo",
        href_template="https://example.com/p/{gtin}",
        title="Product information",
        media_type="text/html",
        is_default=True,
    ),
    # Needs a lot, so it is offered for /01/{gtin}/10/{lot} and skipped for a bare GTIN.
    LinkTemplate(
        link_type="gs1:traceability",
        href_template="https://example.com/trace/{gtin}/{lot}",
        title="Traceability",
        media_type="text/html",
    ),
    LinkTemplate(
        link_type="gs1:epcis",
        href_template="https://api.example.com/epcis",
        title="EPCIS query interface",
        media_type="application/json",
    ),
]

app = FastAPI(title="Minimal GS1 Digital Link resolver")
app.include_router(
    build_resolver_router(
        templates=TEMPLATES,
        # The address this resolver answers on: what a QR code would be printed with.
        resolver_base_url="http://127.0.0.1:8000",
    )
)
