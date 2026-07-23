# Security Policy

This repository is private and all rights are reserved.

## Reporting a vulnerability

Do not disclose vulnerabilities in public issues, discussions, commits, or pull requests. Report them privately to the repository owner with:

- the affected component and version/commit
- reproduction steps
- expected and observed behavior
- potential impact
- suggested mitigation, if known

Do not include active credentials, authentication cookies, personal data, or uploaded documents in a report.

## Credential handling

- Active backend credentials belong only in `backend/.env`.
- Browser-exposed configuration must be limited to intentionally public `VITE_*` values.
- `.env.example` files must contain placeholders only.
- If a secret is committed or shared, revoke it at the provider and replace the local value.

## Sensitive data

`backend/storage/` may contain user-uploaded documents and is excluded from version control. Database dumps, logs, screenshots, and test fixtures must not include personal or authentication data.

## Supported versions

Security fixes are applied to the current development branch. Older snapshots are not maintained unless explicitly stated by the repository owner.
