# iqoqo Release Process

We use an automated release process tied to GitHub Actions.

## How to create a new release

1. **Create a release branch**: Branch off from `main` (e.g., `git checkout -b release/0.2.0`).
2. **Update Versions**: 
   - Bump the version in `pyproject.toml`.
   - Bump the version in `frontend/package.json` (to keep it synced).
3. **Update Changelog**: Move items from `## [Unreleased]` in `docs/CHANGELOG.md` to a new section `## [0.2.0] - YYYY-MM-DD`.
4. **Commit and Push**: `git commit -am "chore: prep release v0.2.0"` and push the branch.
5. **Create a Pull Request**: Open a PR from `release/0.2.0` into `main`.
6. **Merge**: Once approved, merge the PR. 

Upon merge, the GitHub Action will automatically:
- Read the version from `pyproject.toml`.
- Extract the notes from `CHANGELOG.md`.
- Build and push `iqoqo-backend` and `iqoqo-frontend` to the GitHub Container Registry.
- Create a Git Tag (e.g., `v0.2.0`) and a formal GitHub Release.
