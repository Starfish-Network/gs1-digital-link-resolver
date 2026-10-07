# Contributing

Issues and pull requests are welcome, particularly around conformance: if this resolver
disagrees with the GS1 Digital Link standard somewhere, that is a bug worth reporting even
without a fix attached.

## Running it locally

```bash
pip install -e ".[test,example]"
pytest
uvicorn examples.minimal_resolver:app
```

## What a change needs

A test. The suite is fast and runs offline, so there is no reason for a behaviour change to
arrive without one.

Parsing and resolution stay free of transport, authentication and storage concerns. That
separation is what lets the package front a different back end, so a change that reaches
for a database or a credential belongs in the application mounting the router, not here.

Resolution must stay identity-blind. A resolver answers from the URL alone and the same
scan returns the same answer to everybody; anything that varies the response by who is
asking defeats the model and is out of scope for this package.

## Style

`ruff check .` and `ruff format --check .` run in CI. Comments explain why, not what.
