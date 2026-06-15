# Contributing

Thanks for helping improve AI Overlay Agent.

## How to Contribute

1. Fork the repository.
2. Create a focused branch.
3. Make your change with clear commits.
4. Run the relevant smoke checks.
5. Open a pull request with a short description, screenshots for UI changes, and any testing notes.

## Branch Naming

Use short, descriptive branch names:

- `feature/model-selector`
- `fix/hotkey-registration`
- `docs/install-guide`
- `chore/dependency-update`

## Pull Request Process

- Keep pull requests focused on one feature or fix.
- Explain the user-visible behavior change.
- Link related issues when applicable.
- Include before/after screenshots for visual changes.
- Note any follow-up work that is intentionally left out.

## Coding Guidelines

- Follow the existing Python style and module boundaries.
- Prefer small functions with explicit names.
- Keep UI behavior responsive; avoid blocking the tkinter main thread.
- Do not commit local `.env` files, API keys, screenshots containing sensitive data, or generated build outputs.
- Update documentation when setup, configuration, or behavior changes.

## Issue Reporting

When filing an issue, include:

- Operating system and Python version.
- How you installed or ran the app.
- Steps to reproduce the problem.
- Expected behavior and actual behavior.
- Relevant logs or screenshots with secrets removed.
