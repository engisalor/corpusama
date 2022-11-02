# Humanitarian Encyclopedia Template Repository

This repository serves as a template for adding new projects to Github. It's preconfigured for Python -- alter as needed.

**Getting started**

- use [release-please](https://github.com/googleapis/release-please) for version control
  - be sure to follow [conventional commits](https://www.conventionalcommits.org)
  - `CHANGELOG.md` is updated automatically (don't edit manually)
- use [pre-commit](https://pre-commit.com/) for standardizing code and quality control
  - install and configure pre-commit locally
  - see `.pre-commit-config` for commit hooks and urls for more information
- use `main` as the primary branch name
- add a name to `pyproject.toml`
- add a LICENSE file as appropriate
- overwrite this README with the project's own content
- update this template with improvements