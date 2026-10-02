# GS1 Digital Link resolver

A GS1 Digital Link is an identifier written as an HTTPS URL. `/01/09506000134352/10/ABC123`
is GTIN 09506000134352, lot ABC123, and a scanner reads it straight off a package.

This library parses that URL into the application identifiers it carries and resolves them
to links for that specific item, as a FastAPI router you can mount in your own service.

```python
from fastapi import FastAPI
from gs1_digital_link import LinkTemplate, build_resolver_router

app = FastAPI()
app.include_router(
    build_resolver_router(
        templates=[
            LinkTemplate(
                link_type="gs1:productInfo",
                href_template="https://example.com/p/{gtin}",
                is_default=True,
            ),
            LinkTemplate(
                link_type="gs1:traceability",
                href_template="https://example.com/trace/{gtin}/{lot}",
            ),
        ],
        resolver_base_url="https://id.example.com",
    )
)
```

A scan of `https://id.example.com/dl/01/09506000134352/10/ABC123` then answers `307` to
`https://example.com/p/09506000134352`, with the alternatives in an RFC 8288 `Link` header.
Change the lot and the answer changes.

## What it does

Resolution is template substitution over the identifier that was scanned, so two lots of
one product resolve to two different pages. A template whose placeholders the identifier
cannot fill is skipped rather than rendered with a blank: a lot-level link does not apply
to a scan that carried no lot.

Parsing handles an arbitrary stem before the first identifier, GS1's alphanumeric short
names (`/gtin/…/lot/…`), percent-encoded values, and the qualifier ordering the standard
requires. GTIN-8, 12 and 13 are normalised to GTIN-14, so two spellings of one trade item
compare equal. Check digits are validated, and a mistyped identifier fails with a `400`
rather than redirecting somewhere plausible and wrong.

Ask for `?linkType=all`, or send `Accept: application/linkset+json`, and you get the whole
linkset instead of a redirect. `/.well-known/gs1resolver` serves a discovery document.

## It never learns who is asking

A resolver routes on what is in the URL and nothing else. It has no database, no session
and no credential, and its answer is a pure function of the path: two people scanning the
same package get byte-identical responses.

That is deliberate, and it is why resolution is unauthenticated. A label cannot know who
is holding it, so a role in the path could only ever pick a rendering, never grant access.
A `linkType` says what the caller wants, never who they are, and so can never widen access
either. Authorization belongs to the application the resolver redirects to, decided from
that caller's own session once the browser has arrived.

## Mounting

The router is served under a `/dl` stem by default. The standard permits any stem before
the first application identifier, and keeping one stops the catch-all resolver route
shadowing the rest of your API. Pass `stem="/id"`, or any other, to move it.

Templates may be a list, or a callable returning one when they depend on runtime
configuration. `resolver_base_url` accepts the same.

## Supported identifiers

Every GS1 Digital Link primary key: GTIN, SSCC, GDTI, GCN, GINC, GSIN, GLN, PGLN, GRAI,
GIAI, ITIP, CPID, GMN and both GSRN forms, with the qualifiers each admits. Application
identifiers that are not qualifiers of the primary key, in the path or the query string,
are carried as attributes and are available to templates by their AI code.

## Install

```bash
pip install gs1-digital-link-resolver
```

Python 3.11 or later. Depends on pydantic and fastapi, nothing else.

## Tests

```bash
pip install -e ".[test]"
pytest
```

## Background

Written at [Starfish Network](https://starfish-network.com) and contributed to the Supply
Chain of the Future (SCOTF) collaboration, which wanted an open implementation of the GS1
Digital Link standard that anyone can run in front of their own system.

## Licence

Apache-2.0. See [LICENSE](LICENSE).
