# Changelog

## 0.1.0

First release.

Parses a GS1 Digital Link URI into its application identifiers, tolerating an arbitrary
stem, GS1's alphanumeric short names and percent-encoded values. Normalises GTIN-8, 12 and
13 to GTIN-14, validates check digits, and enforces the qualifier ordering the standard
requires.

Resolves an identifier to a linkset by substituting it into caller-supplied templates, so
two lots of a product resolve to two different links and a template the identifier cannot
fill is skipped rather than rendered blank.

Serves the resolver as a FastAPI router: 307 to the default link with the alternatives in
an RFC 8288 `Link` header, the full linkset under `?linkType=all` or
`Accept: application/linkset+json`, and a `/.well-known/gs1resolver` discovery document.
