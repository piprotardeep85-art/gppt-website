# AI JobTrust Architecture

The MVP separates the Flutter client, FastAPI service, React admin and database.
The detection engine is deterministic and explainable. AI provider integration is
deliberately provider-abstracted so secrets stay in the backend.

## Request flow

1. The client submits job text or a URL.
2. FastAPI validates request size and fields.
3. Rule detection extracts exact matched snippets.
4. Severity is combined with a conservative transparent policy.
5. URL requests are resolved and checked against private/reserved IP ranges.
6. The API returns evidence, categories, limitations and safe actions.

## Risk policy

- Critical indicator: High Risk
- High or medium indicator: Suspicious
- No matched indicator: Not Verified
- No numerical confidence is fabricated.
