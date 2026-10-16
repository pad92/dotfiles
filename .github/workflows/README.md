# CI Workflows

This repository is hosted on **GitHub**, **GitLab** (`.gitlab-ci.yml`), and a
self-hosted **Gitea** instance. Workflows that share CI logic use scripts from
[`scripts/ci/`](../../scripts/ci).

> [!NOTE]
> A Gitea Actions runner also scans `.github/workflows`, so these files run on
> Gitea too unless explicitly scoped. See [Multi-forge notes](#multi-forge-notes).

## Workflows

| File | Trigger | Purpose |
| --- | --- | --- |
| [`deploy-pages.yml`](deploy-pages.yml) | Push or PR to `main` (documentation paths) | Build the documentation site and deploy it to GitHub Pages. |
| [`package-vim.yml`](package-vim.yml) | Push or PR to `main` (Vim paths) | Package the Vim configuration as `vim.tar.gz`. |
| [`package-nvim.yml`](package-nvim.yml) | Push or PR to `main` (Neovim paths) | Package `.config/nvim` as `nvim.tar.gz`. |
| [`release.yml`](release.yml) | Push a `v*` tag | Publish a release with notes from `CHANGELOG.md`. |

### `deploy-pages.yml`

Installs `markdown` and runs [`scripts/ci/build_pages.sh`](../../scripts/ci/build_pages.sh).
The script uses [`gen_pages.py`](../../scripts/ci/gen_pages.py) to render
`README.md`, `CHANGELOG.md`, and `dist/arch/install.md` into `public/`. Each run
uploads the artifact; only runs on `main` deploy it.

`build_pages.sh` is the single source for the page list. The local
`post-commit` preview hook (see `.pre-commit-config.yaml`) and GitLab `pages`
job use the same script.

### `package-vim.yml`

Checks out submodules recursively, then packages the Vim configuration as a
`vim-package` artifact.

### `package-nvim.yml`

Packages `.config/nvim` as an `nvim-package` artifact when that configuration
changes.

### `release.yml`

When a `v*` tag is pushed, the workflow:

1. runs [`scripts/ci/extract_release_notes.sh`](../../scripts/ci/extract_release_notes.sh)
   to pull that version's section out of `CHANGELOG.md`;
2. creates the release via the REST API
   (`POST $GITHUB_API_URL/repos/$GITHUB_REPOSITORY/releases`) using `jq` + `curl`.

The same API request works on GitHub and Gitea. Both runners provide
`GITHUB_API_URL`, `GITHUB_REPOSITORY`, and `secrets.GITHUB_TOKEN`, allowing the
workflow to publish releases on either forge.

> [!IMPORTANT]
> The release notes are read from `CHANGELOG.md` **at the tagged commit**.
> Add the `## [vX.Y.Z]` section before pushing the tag. Without it, the release
> uses the placeholder "No specific notes found".

## Shared scripts (`scripts/ci/`)

| Script                     | Used by                                                      |
| -------------------------- | ------------------------------------------------------------ |
| `build_pages.sh`           | `deploy-pages.yml`, GitLab `pages`, local `post-commit` hook |
| `extract_release_notes.sh` | `release.yml`, GitLab `create_release`                       |
| `gen_pages.py`             | `build_pages.sh`                                             |

Both shell scripts use **POSIX `sh`**, so they run on minimal CI images such as
GitLab's Alpine image.

## Variables & secrets

The runners provide the tokens used by these workflows; no custom secrets or
variables are needed.

| Name                           | Used by            | Source                                                   | Manual setup |
| ------------------------------ | ------------------ | -------------------------------------------------------- | ------------ |
| `GITHUB_TOKEN`                 | `release.yml`      | Auto-injected by GitHub Actions **and** the Gitea runner | None         |
| OIDC token (`id-token: write`) | `deploy-pages.yml` | Auto-issued by GitHub for Pages                          | None         |

> [!NOTE]
> `release.yml` declares `permissions: contents: write` to let the automatic
> token create releases. This permission is set in the workflow, not in the
> repository settings.

One-time setup prerequisites (not variables):

- **GitHub Pages** must be enabled for `deploy-pages.yml`: _Settings → Pages →
  Build and deployment → Source: GitHub Actions_. The job deploys to the
  `github-pages` environment.
- **Gitea**: Enable Actions for the repository. The runner injects `GITHUB_TOKEN`
  with write access to the current repository, which is enough to create
  releases. No secret needs to be added.

## Multi-forge notes

Because Gitea's runner also picks up `.github/workflows`:

- **`release.yml`** is intentionally forge-agnostic and runs on both GitHub and
  Gitea.
- **`deploy-pages.yml`**, **`package-vim.yml`**, and **`package-nvim.yml`** use
  GitHub-specific features (Pages or artifact upload), so their jobs are
  guarded with:

  ```yaml
  if: ${{ github.server_url == 'https://github.com' }}
  ```

  On Gitea, `github.server_url` is the instance URL and those jobs skip. On
  GitHub, they run normally.
