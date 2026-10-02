"""A conformant GS1 Digital Link resolver, as a router any FastAPI app can mount.

Resolution is unauthenticated by design. A resolver routes on what is in the URL and
never learns who is asking, so entitlement belongs to whatever application it redirects
to, decided from that caller's own session. A ``linkType`` says what the caller wants,
never who they are, and so can never widen access.

Nothing here knows about any particular back end: callers supply the link templates and
the address the resolver answers on, which is what lets the same code front a different
system.
"""

import logging
from collections.abc import Callable, Sequence

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse

from gs1_digital_link.application_identifiers import PRIMARY_KEY_QUALIFIERS
from gs1_digital_link.digital_link import DigitalLinkError, parse_digital_link
from gs1_digital_link.linkset import (
    LINK_TYPE_ALL,
    LinkTemplate,
    link_header,
    resolve_links,
)

logger = logging.getLogger(__name__)

DEFAULT_STEM = "/dl"
WELL_KNOWN_PATH = "/.well-known/gs1resolver"
LINKSET_MEDIA_TYPE = "application/linkset+json"

TemplateSource = Sequence[LinkTemplate] | Callable[[], Sequence[LinkTemplate]]
"""Templates may be supplied directly, or as a callable when they depend on runtime config."""


def _resolve_templates(templates: TemplateSource) -> Sequence[LinkTemplate]:
    return templates() if callable(templates) else templates


def _wants_linkset(request: Request, link_type: str | None) -> bool:
    if link_type == LINK_TYPE_ALL:
        return True
    return LINKSET_MEDIA_TYPE in request.headers.get("accept", "")


def build_resolver_router(
    *,
    templates: TemplateSource,
    resolver_base_url: Callable[[], str] | str,
    stem: str = DEFAULT_STEM,
) -> APIRouter:
    """Build a router serving the resolver and its discovery document.

    ``stem`` is the path the identifier follows. The standard permits any stem before the
    first application identifier, and keeping one stops the catch-all route shadowing the
    rest of a host's API.
    """
    router = APIRouter()


    def _base_url() -> str:
        return resolver_base_url() if callable(resolver_base_url) else resolver_base_url

    async def _gs1_resolver_discovery() -> JSONResponse:
        available = _resolve_templates(templates)
        return JSONResponse(
            {
                "resolverRoot": f"{_base_url()}{stem}",
                "supportedPrimaryKeys": sorted(PRIMARY_KEY_QUALIFIERS),
                "supportedLinkTypes": sorted({template.link_type for template in available}),
            }
        )

    async def _resolve_digital_link(
        identifier_path: str,
        request: Request,
        linkType: str | None = Query(
            default=None,
            alias="linkType",
            description="Link type to return, or 'all' for the full linkset.",
        ),
    ) -> JSONResponse | RedirectResponse:
        try:
            uri = parse_digital_link(identifier_path, dict(request.query_params))
        except DigitalLinkError as error:
            logger.info(f"Digital link resolver rejected {identifier_path!r}: {error}")
            raise HTTPException(status_code=400, detail=str(error)) from error

        linkset = resolve_links(uri, _resolve_templates(templates), link_type=linkType)
        default = linkset.default()
        if default is None:
            raise HTTPException(
                status_code=404,
                detail=f"No {linkType or 'default'} link is available for {uri.canonical_path()}",
            )

        if _wants_linkset(request, linkType):
            return JSONResponse(linkset.model_dump(exclude_none=True))

        # Alternatives travel in the Link header so a client that followed the redirect
        # can still discover the other link types without a second round trip.
        return RedirectResponse(
            url=default.href,
            status_code=307,
            headers={"Link": link_header(linkset)},
        )

    router.add_api_route(
        WELL_KNOWN_PATH,
        _gs1_resolver_discovery,
        methods=["GET"],
        description="GS1 Digital Link resolver discovery document (RFC 8615).",
    )
    router.add_api_route(
        f"{stem}/{{identifier_path:path}}",
        _resolve_digital_link,
        methods=["GET"],
        description=(
            "Resolve a GS1 Digital Link. Redirects (307) to the default link for the scanned "
            "identifier, or returns the full linkset when linkType=all is given or "
            "application/linkset+json is requested."
        ),
        # The handler chooses between a redirect and a body at request time, so there is
        # no single response model to infer.
        response_model=None,
    )

    return router
