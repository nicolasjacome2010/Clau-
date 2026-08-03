# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository state

This repository is currently a bare scaffold with no source code, build configuration, or tests. It contains only:

- `README.md` — a one-line project description: "Clau- / Autonomous reality"
- `LICENSE` — MIT License (2026, nicolasjacome2010)
- `.gitignore` — a standard Python `.gitignore` (covers virtualenvs, `__pycache__`, packaging artifacts, pytest/mypy/ruff caches, etc.)

There is no application code, package manifest (no `pyproject.toml`, `requirements.txt`, `package.json`, etc.), no CI configuration, and no test suite yet. The `.gitignore` suggests Python is the intended language for this project, but no framework or structure has been established.

## Working in this repository

Since there is no existing architecture or tooling to follow, there are no commands to build, lint, or test. When adding the first code to this repository:

- Establish a dependency/build manifest appropriate to the stack actually being used (don't assume Python beyond what the `.gitignore` implies — confirm with the user if the intended stack is unclear).
- Once real source files, a manifest, and tests exist, update this CLAUDE.md with the actual build/lint/test commands and a description of the real architecture — do not leave this file describing an empty scaffold once that's no longer true.
