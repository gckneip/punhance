# Releasing

This project publishes prebuilt Linux and Windows binaries automatically via GitHub Actions. This doc explains how that pipeline works and how to cut a new release.

Workflow file: [`.github/workflows/release.yml`](../.github/workflows/release.yml)

## Trigger

The workflow runs on:

- **A tag push matching `v*.*.*`** (e.g. `v1.0.0`, `v0.2.3`). Tags that don't match this pattern (`latest`, `v1.0`, `release-1`, ...) do **not** trigger it.
- **Manual dispatch** (`workflow_dispatch`) from the *Actions* tab on GitHub — see the caveat below.

Regular pushes to `main` or any other branch never trigger a release build.

## What happens on a run

1. **`build` job** — runs as a matrix across `ubuntu-latest` and `windows-latest`:
   - Installs `requirements.txt` plus `pyinstaller`.
   - Packages the app with:
     ```
     pyinstaller --onefile --windowed --name finance-manager --paths . src/main.py
     ```
   - Renames the resulting binary to a fixed asset name and uploads it as a build artifact:
     - Linux → `finance-manager-linux`
     - Windows → `finance-manager-windows.exe`
2. **`release` job** — runs after both builds succeed:
   - Downloads both artifacts.
   - Uses [`softprops/action-gh-release`](https://github.com/softprops/action-gh-release) to create a GitHub Release for the pushed tag and attach both binaries as release assets.

No manual upload step is needed — pushing the tag is the only action required to publish.

## How to cut a release

1. Make sure `main` is in the state you want to ship — there are no automated tests gating this pipeline (see [Known limitations](#known-limitations)), so verify manually first.
2. Pick a version following `vMAJOR.MINOR.PATCH`. There is no version file in the repo — the git tag is the only source of the version number.
3. Tag and push:
   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```
4. Watch the **Actions** tab — the `Build and Release` workflow builds both binaries and publishes them to a new GitHub Release.
5. Nothing else to update: the README's download buttons point at `.../releases/latest/download/<asset name>`, which GitHub always resolves to the newest release. If you ever rename the assets in the workflow, update the links in `README.md` to match.

## Manual runs (`workflow_dispatch`)

You can trigger the workflow by hand from the Actions tab without pushing a tag — useful to sanity-check that the PyInstaller build still succeeds on both platforms after a dependency bump.

**Caveat:** the `release` job asks `softprops/action-gh-release` to publish a release for the current git ref. When triggered manually from a branch (not a tag), there is no tag to attach to, so `release` fails even if both `build` jobs succeed. A manual run is only reliable for checking the `build` job in isolation — an actual release still requires a tag push.

## Secrets

None to configure. `GITHUB_TOKEN` is provided automatically by GitHub Actions and already has enough permission to create releases in this repo.

## Known limitations

- No automated tests run before packaging, so a broken `main` can still produce a "successful" release build.
- No macOS build.
- Binaries are not code-signed or notarized — Windows SmartScreen will warn on first run, and the Linux binary needs `chmod +x` after download (GitHub strips the executable bit).
- Release notes are not auto-generated; edit the release description manually on GitHub if you want changelog text.
