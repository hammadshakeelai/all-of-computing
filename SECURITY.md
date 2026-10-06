# Security and private data

This v1 application is intended for one trusted user on their local computer. It binds to loopback; public hosting and shared accounts are not supported. Keep Python and your browser maintained. Do not expose the port through tunnels or a public reverse proxy without designing appropriate authentication and deployment controls.

Personal learning records belong in `private/` or another private data location, outside public commits. API keys belong in the process environment. Backups and screenshots can contain sensitive material even when they contain no credentials. Optional cloud tutoring sends selected content to the configured provider after being enabled; see [setup](docs/GETTING-STARTED.md).

## Report a vulnerability

Use the repository's **Security → Report a vulnerability** private reporting form when available. Do not put exploitable details, credentials, private answers, or database archives in public issues. If private reporting is unavailable, open a minimal public issue requesting a private reporting channel without disclosing the vulnerability itself.

Include the affected commit, reproduction using synthetic data, impact, and suggested mitigation if known. No response-time or support guarantee is currently offered. If a credential has leaked, revoke it with the provider rather than relying on deleting the Git file.

The current main branch is the maintenance target. See [release validation and limitations](docs/RELEASE.md); mock provider tests do not establish live provider or educational accuracy.
