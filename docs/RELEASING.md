# Releasing Undex

Initial release: `v0.1.0`, squash-integrated from `dev` into `main`. The project is a source
bundle (`tool.uv.package = false`), not a Python package for publication to PyPI.

Release preparation creates notes and local assets. Tagging, pushing, and creating
or publishing a GitHub release are separate explicit steps.

## Before publication

- Confirm `pyproject.toml`, `uv.lock`, changelog, notes, and asset names agree on the version.
- Confirm the MIT `LICENSE` and copyright notice are included in the source archive.
- Run the checks below on the exact final tree and record any verification limits.
- Validate installation on a disposable Ubuntu host, including first install,
  rerun, browser dependencies, and device authorization. Keep personal account
  credentials outside release artifacts. If publishing before this validation,
  identify the release as a preview and retain the known limits in its notes.
- Review the archive for unexpected files and verify its checksum after download.
- Commit the reviewed release preparation before creating its final tag/archive.

## Local checks

```bash
uv run --locked python -m unittest discover -s tests -v
uvx --from shellcheck-py shellcheck -x install.sh lib/*.sh bin/undex-graphify
for file in install.sh bin/undex-graphify lib/*.sh; do bash -n "$file" || exit; done
git diff --check
git status --short
```

## Build the final source archive

After the release preparation is committed and the tag is explicitly approved:

```bash
git tag -a v0.1.0 -m "Undex v0.1.0"
mkdir -p dist
git archive --format=tar.gz --prefix=undex-0.1.0/ v0.1.0 > dist/undex-0.1.0.tar.gz
(cd dist && sha256sum undex-0.1.0.tar.gz > SHA256SUMS)
(cd dist && sha256sum -c SHA256SUMS)
tar -tzf dist/undex-0.1.0.tar.gz
```

The archive contains only the tagged source tree. It excludes `.git`, local
virtual environments, ignored state, and generated release assets. A candidate
archive built before the release commit must be rebuilt from the final tag;
its checksum can change when notes or licensing change.

Extract the final archive into a temporary directory and run the same tests from
there. Check that `install.sh`, `bin/undex-graphify`, and the external-command test
fixture retain executable permissions. The archive must contain `uv.lock`, all ten
agent roles, and every installer module.

## Publish when authorized

Push the reviewed branch and tag:

```bash
git push origin main
git push origin v0.1.0
```

On GitHub, open **Releases → Draft a new release**, select the existing tag, use
`Undex v0.1.0` as the title, paste the notes from `docs/releases/v0.1.0.md`, and
attach both assets. Save the draft before publishing. GitHub CLI is not required.

Remove the draft-status sentence from the notes and set the changelog release date
when publication is actually approved. Review the GitHub draft, use the prerelease
setting if this is still a preview, and publish explicitly. Do not treat a local
archive or a passing command-double suite as evidence that publication occurred.
