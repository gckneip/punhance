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
2. **`release` job** — runs after both builds succeed, with an explicit `permissions: contents: write` (needed to create a release and upload assets - see [Troubleshooting](#troubleshooting)):
   - Downloads both artifacts.
   - Uses [`softprops/action-gh-release`](https://github.com/softprops/action-gh-release) to create a GitHub Release for the pushed tag and attach both binaries as release assets.

No manual upload step is needed — pushing the tag is the only action required to publish.

## How to cut a release

1. Make sure `main` is in the state you want to ship — there are no automated tests gating this pipeline (see [Known limitations](#known-limitations)), so verify manually first.
2. Update `CHANGELOG.md` at the repo root with a new `## [vMAJOR.MINOR.PATCH] - YYYY-MM-DD` section (`Added`/`Changed`/`Fixed`, [Keep a Changelog](https://keepachangelog.com/) style) covering everything since the previous tag. Commit it to `main` before tagging.
3. Pick a version following `vMAJOR.MINOR.PATCH`. There is no version file in the repo — the git tag is the only source of the version number.
4. Tag and push:
   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```
5. Watch the **Actions** tab (or `gh run watch <run-id>`) — the `Build and Release` workflow builds both binaries and publishes them to a new GitHub Release.
6. Paste that version's `CHANGELOG.md` section into the release notes:
   ```bash
   gh release edit v0.2.0 --notes-file CHANGELOG.md
   ```
   (`--notes-file` replaces the whole body, so if `CHANGELOG.md` accumulates multiple versions over time, extract just the new section into a temp file first rather than pasting the entire file.)
7. Nothing else to update: the README's download buttons point at `.../releases/latest/download/<asset name>`, which GitHub always resolves to the newest release. If you ever rename the assets in the workflow, update the links in `README.md` to match.

### If a tagged run already failed before you fixed something

Deleting and recreating the tag on the fixed commit is fine as long as the GitHub Release from the failed run was never actually published (check `gh release list` first) — re-pushing the tag re-triggers a clean build:
```bash
gh run list --limit 3                        # confirm the run actually failed, and no release exists
git push --delete origin v0.2.0
git tag -d v0.2.0
git tag -a v0.2.0 -m "v0.2.0"                 # recreate on the current (fixed) HEAD
git push origin v0.2.0
```

## Manual runs (`workflow_dispatch`)

You can trigger the workflow by hand from the Actions tab without pushing a tag — useful to sanity-check that the PyInstaller build still succeeds on both platforms after a dependency bump.

**Caveat:** the `release` job asks `softprops/action-gh-release` to publish a release for the current git ref. When triggered manually from a branch (not a tag), there is no tag to attach to, so `release` fails even if both `build` jobs succeed. A manual run is only reliable for checking the `build` job in isolation — an actual release still requires a tag push.

## Secrets

None to configure. `GITHUB_TOKEN` is provided automatically by GitHub Actions. It defaults to read-only in this repo's settings (Settings → Actions → General → Workflow permissions), which is why the `release` job declares its own `permissions: contents: write` rather than relying on the repo-wide default - see [Troubleshooting](#troubleshooting).

## Troubleshooting

**`release` job fails at "Create Release" with `Resource not accessible by integration`.** This means `GITHUB_TOKEN` didn't have `contents: write` for that run. Happened on the very first release (v0.1.0, run `34517952404`) because the repo's default workflow permissions were read-only and `release.yml` didn't yet declare its own `permissions:` block. Fixed by adding `permissions: contents: write` under the `release` job (commit `2e0b282`) - if it recurs (e.g. after copying this workflow into another repo), either add that block or flip the repo's default to "Read and write permissions." The `build` jobs are unaffected and their artifacts are still uploaded even when `release` fails, so you don't need to rebuild - just fix permissions and re-push the tag (see [above](#if-a-tagged-run-already-failed-before-you-fixed-something)) or re-run the failed job with `gh run rerun --failed` if the repo-wide default was the fix (a re-run picks up current repo settings; it does *not* pick up a new commit's workflow file, so a code-level fix like the `permissions:` block still needs a fresh tag push).

## Known limitations

- No automated tests run before packaging, so a broken `main` can still produce a "successful" release build.
- No macOS build.
- Binaries are not code-signed or notarized — Windows SmartScreen will warn on first run, and the Linux binary needs `chmod +x` after download (GitHub strips the executable bit).
- `gh release edit --notes-file` needs the `workflow` scope on top of `repo` only if you're also pushing changes to files under `.github/workflows/` in the same session (`gh auth refresh -h github.com -s workflow` if `git push` rejects a workflow-file change with "refusing to allow an OAuth App to create or update workflow ... without `workflow` scope").
