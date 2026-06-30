# CI Workflows

GitHub Actions workflows for this repository. The repo is hosted on **GitHub**,
**GitLab** (`.gitlab-ci.yml`), and a self-hosted **Gitea** instance, so the
forge-specific logic is kept thin and the real work lives in reusable scripts
under [`.ci_bin/`](../../.ci_bin).

> [!NOTE]
> A Gitea Actions runner also scans `.github/workflows`, so these files run on
> Gitea too unless explicitly scoped. See [Multi-forge notes](#multi-forge-notes).

## 🔄 Workflows

| File                                   | Trigger                       | Purpose                                                          |
| -------------------------------------- | ----------------------------- | ---------------------------------------------------------------- |
| [`deploy-pages.yml`](deploy-pages.yml) | push/PR to `main` (doc paths) | Build the static docs site and deploy it to GitHub Pages.        |
| [`package-vim.yml`](package-vim.yml)   | push/PR to `main` (Vim paths) | Package `.vim`/`.vimrc` into a `vim.tar.gz` artifact.            |
| [`release.yml`](release.yml)           | push tag `v*`                 | Publish a release whose notes are extracted from `CHANGELOG.md`. |

### 🚀 `deploy-pages.yml`

Installs `markdown` and runs [`.ci_bin/build_pages.sh`](../../.ci_bin/build_pages.sh),
which renders `README.md`, `CHANGELOG.md`, and `dist/arch/install.md` into
`public/` via [`gen_pages.py`](../../.ci_bin/gen_pages.py). The artifact is
uploaded on every run; deployment only happens on `main`.

The page list lives **only** in `build_pages.sh` — the same script backs the
local `post-commit` preview hook (see `.pre-commit-config.yaml`) and the GitLab
`pages` job, so all three stay in sync.

### 📦 `package-vim.yml`

Checks out submodules recursively and tars the Vim configuration into a
`vim-package` artifact.

### 🏷️ `release.yml`

On a `v*` tag it:

1. runs [`.ci_bin/extract_release_notes.sh`](../../.ci_bin/extract_release_notes.sh)
   to pull that version's section out of `CHANGELOG.md`;
2. creates the release via the REST API
   (`POST $GITHUB_API_URL/repos/$GITHUB_REPOSITORY/releases`) using `jq` + `curl`.

The API call is **forge-agnostic**: GitHub and Gitea expose the same release
endpoint and both inject `GITHUB_API_URL`, `GITHUB_REPOSITORY`, and
`secrets.GITHUB_TOKEN`, so this one workflow publishes releases on either forge.

> [!IMPORTANT]
> The release notes are read from `CHANGELOG.md` **at the tagged commit**.
> Make sure the `## [vX.Y.Z]` section exists before pushing the tag, otherwise
> the release gets a "No specific notes found" placeholder.

## 🔧 Shared scripts (`.ci_bin/`)

| Script                     | Used by                                                      |
| -------------------------- | ------------------------------------------------------------ |
| `build_pages.sh`           | `deploy-pages.yml`, GitLab `pages`, local `post-commit` hook |
| `extract_release_notes.sh` | `release.yml`, GitLab `create_release`                       |
| `gen_pages.py`             | `build_pages.sh`                                             |

Both shell scripts are **POSIX `sh`** (no Bash-isms) so they run on minimal CI
images such as the GitLab `alpine` job.

## 🔐 Variables & secrets

No custom secrets or variables need to be configured — every token used is
provided automatically by the runner.

| Name                           | Used by            | Source                                                   | Manual setup |
| ------------------------------ | ------------------ | -------------------------------------------------------- | ------------ |
| `GITHUB_TOKEN`                 | `release.yml`      | Auto-injected by GitHub Actions **and** the Gitea runner | None         |
| OIDC token (`id-token: write`) | `deploy-pages.yml` | Auto-issued by GitHub for Pages                          | None         |

> [!NOTE]
> `release.yml` declares `permissions: contents: write` so the automatic token
> is allowed to create releases — this lives in the workflow, not in repo
> settings.

One-time setup prerequisites (not variables):

- **GitHub Pages** must be enabled for `deploy-pages.yml`: _Settings → Pages →
  Build and deployment → Source: GitHub Actions_. The job deploys to the
  `github-pages` environment.
- **Gitea**: Actions must be enabled for the repo. The runner injects
  `GITHUB_TOKEN` automatically with write access to the current repo (enough to
  create releases) — no secret to add.

## 🍴 Multi-forge notes

Because Gitea's runner also picks up `.github/workflows`:

- **`release.yml`** is intentionally forge-agnostic and runs on both GitHub and
  Gitea.
- **`deploy-pages.yml`** and **`package-vim.yml`** are GitHub-specific (GitHub
  Pages / artifact upload), so each job is guarded with:

  ```yaml
  if: ${{ github.server_url == 'https://github.com' }}
  ```

  On Gitea `github.server_url` is the instance URL, so those jobs skip; on
  GitHub they run as normal.
