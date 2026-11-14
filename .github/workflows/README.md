# CI Workflows

This repository is hosted on **GitHub**, **GitLab** (`.gitlab-ci.yml`), and a
self-hosted **Gitea** instance. Workflows that share CI logic use scripts from
[`scripts/ci/`](../../scripts/ci).

> [!NOTE]
> A Gitea Actions runner also scans `.github/workflows`, so these files run on
> Gitea too unless explicitly scoped. See [Multi-forge notes](#multi-forge-notes).

## Workflows

| File                                   | Trigger                                    | Purpose                                                     |
| -------------------------------------- | ------------------------------------------ | ----------------------------------------------------------- |
| [`deploy-pages.yml`](deploy-pages.yml) | Push or PR to `main` (documentation paths) | Build the documentation site and deploy it to GitHub Pages. |
| [`package-vim.yml`](package-vim.yml)   | Push or PR to `main` (Vim paths)           | Package the Vim configuration and plugins as `vim.tar.gz`.  |
| [`package-nvim.yml`](package-nvim.yml) | Push or PR to `main` (Neovim paths)        | Package `.config/nvim` as `nvim.tar.gz`.                    |
| [`release.yml`](release.yml)           | Push a `v*` tag                            | Publish a release with notes from `CHANGELOG.md`.           |

### `deploy-pages.yml`

Installs `markdown` and `pygments` and runs [`scripts/ci/build_pages.sh`](../../scripts/ci/build_pages.sh).
The script uses [`gen_pages.py`](../../scripts/ci/gen_pages.py) to render every
Markdown file tracked by Git into `public/`. Each run uploads the artifact; only
runs on `main` deploy it, and any change to a `.md` file triggers the workflow.

Each page keeps its source path (`dist/arch/install.md` becomes
`dist/arch/install.md/index.html`), except `README.md`, which becomes the site
index, and `.github/`, which is published as `github/` because
`actions/upload-pages-artifact` drops `.github` from the artifact.
`gen_pages.py` rewrites relative links so they work on the site:

- a link to a Markdown file goes to its page, query and anchor included;
- a link starting with `/` is relative to the repository root, as on the forges;
- a linked image is copied into `public/`, under `github/` for `.github/`;
- a link to any other repository file or directory goes to the forge's file
  browser at the built commit (`GITHUB_SHA` here, `CI_COMMIT_SHA` on GitLab).
  The local preview links to the file in the checkout instead.

Only `href` and `src` attributes of real `<a>`, `<img>` and `<source>` tags
are rewritten, so tags shown as code stay as written. A page's title is its
first heading, else its path; the home page takes the site title.

The top menu follows `SITE_NAV` in `gen_pages.py`. A section is one page, a
group of pages, or a directory such as `ansible/`, whose dropdown mirrors the
tree of its Markdown files: the directory's `README.md` as Overview, its other
pages, then one entry per subdirectory. A subdirectory links its own
`README.md`, or shows as a heading without one (`roles/`), and lists its pages
indented below. Directories with no page of their own and a single
subdirectory are folded into one entry (`a/b`). Labels come from the first
heading of each page, or from `NAV_LABELS`, and `NAV_EXCLUDE` keeps role payload
files out of the menu, while they stay published. The section of the current
page is highlighted, and a submenu of more than ten entries is laid out in two
columns on wide screens. With a mouse, the dropdowns open on hover; on touch
screens and in the collapsed menu they open with a click. A new README in a listed directory appears in the
menu without editing `gen_pages.py`.

A link whose target does not exist fails the build, and so does a link to a
heading or anchor that its page lacks: `gen_pages.py` lists the broken links on
stderr and exits 1, which stops the Pages jobs. Heading ids keep accents, as
on GitHub and GitLab (`## Présentation` gets `#présentation`). The
`test-gen-pages` pre-commit hook builds the site on every Markdown change and
catches them before the commit. Each build also removes the files a previous
build left in `public/` for renamed or deleted pages.

Each page's `<head>` holds a description taken from its first paragraph with
text, cut to 160 characters, plus Open Graph and Twitter card tags for link
previews, a canonical URL and an `og:image` (`dist/hyprland.webp`). Every
build, the local preview included, also writes `sitemap.xml` and `robots.txt`.
Their URLs start with `DEFAULT_SITE_URL` (`https://dotfiles.depad.fr/`), the
GitLab Pages domain, where `robots.txt` sits at the root of the host. The
GitHub copy points its canonical URLs there too, so search engines index one
site. `SITE_URL` overrides the default. On a project site such as
`<user>.github.io/<repo>/`, crawlers ignore `robots.txt`: submit the sitemap in
Google Search Console (or Bing Webmaster Tools).

Fenced code blocks follow CommonMark: backtick or tilde fences, closed by a
fence of the same character at least as long, so a four-backtick fence can
show a three-backtick fence as code. The pages use the Gruvbox colours of the
Hyprland desktop: `style.css` takes its dark background, text and accent from
`hyprtoolkit.conf.j2`, and a test checks they match. The theme menu, last in
the navbar, picks Light, Dark or Auto and saves the choice in `localStorage`.
Its button shows the icon of the current choice (sun, moon or half circle).
Auto, the default, follows the desktop's light or dark preference. A script
in `<head>` sets `data-theme` on `<html>` before the page is drawn, and
Gruvbox Light applies under `data-theme="light"`. Without JavaScript the site
stays dark. Code blocks use the Pygments `gruvbox-dark` and `gruvbox-light`
styles. The favicon (`favicon.ico` with 16, 32 and 48 px, `favicon.png` at
192 px and `apple-touch-icon.png` at 180 px) is kept in `scripts/ci/` next
to `style.css` and copied to the root of the site. The CDN stylesheets and scripts carry Subresource Integrity hashes;
`CDN_INTEGRITY` in `gen_pages.py` gives the command to
recompute one. Without Pygments, code blocks render without highlighting.
`build_pages.sh` fails when the `markdown` module is missing in CI (`CI` is
set) and skips the build only for the local hook.

`gen_pages.py` is the single source for the page list. The local `post-commit`
preview hook (see `.pre-commit-config.yaml`) and GitLab `pages` job use the same
script.
`make pages` builds the site into `public/` with `CI=1`, as the Pages jobs do,
then opens `public/index.html` with `xdg-open` (`XDG_OPEN` picks another
command).

### `package-vim.yml`

Packages the Vim configuration as a `vim-package` artifact, with the plugins
pinned in `dotfiles_vim_pack_plugins`. `scripts/ci/fetch_vim_plugins.py` reads
that list from the role defaults and clones each plugin under
`.vim/pack/dotfiles/start/` without its `.git` directory.

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
