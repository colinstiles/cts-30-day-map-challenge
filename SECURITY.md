# Security Policy

## Reporting a Vulnerability

Do not open a public issue for a suspected vulnerability or exposed credential.
Report it privately to the project owner listed in the README, including the affected file or component, a reproduction summary, and any potential impact. Remove or rotate exposed credentials through the approved organization process before sharing further details.

## Project Expectations

- Keep credentials, tokens, certificates, and local environment files out of Git.
- Use HTTPS with certificate verification enabled for external services.
- Pin Python dependencies and review updates before merging them.
- Run the configured pre-commit checks before submitting changes.
- Confirm the target portal, account, and item identifiers before any ArcGIS write operation.
