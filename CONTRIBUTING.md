# Contributing

This repository is private and all rights are reserved. Contributions require explicit authorization from the repository owner.

## Development setup

Follow the root [README](README.md) to start Docker infrastructure, the FastAPI backend, the Arq worker, and the Vite frontend.

Install development dependencies:

```bash
cd backend
pip install -r requirements-dev.txt
```

```bash
cd frontend
npm ci
```

## Change guidelines

- Preserve the existing route → service → provider/repository layering.
- Keep vendor-specific integrations behind provider abstractions.
- Do not commit `.env` files, credentials, uploaded documents, model caches, virtual environments, dependencies, or build output.
- Add or update tests for behavior changes.
- Do not change public API contracts or database migrations without documenting compatibility impact.
- Keep changes focused; avoid unrelated refactors.

## Required checks

Before requesting review:

```bash
cd backend
pytest
```

```bash
cd frontend
npm run lint
npm run build
```

## Pull requests

Include:

- a concise problem statement and solution summary
- affected backend/frontend areas
- test evidence
- migration or environment changes, if any
- screenshots for user-interface changes

Never include real credentials or user-uploaded content in issues, logs, screenshots, or pull requests.
