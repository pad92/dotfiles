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

The workflow installs `markdown` and `pygments`, then runs
[`scripts/ci/build_pages.sh`](../../scripts/ci/build_pages.sh), which renders
every Markdown file tracked by Git into `public/` with
[`gen_pages.py`](../../scripts/ci/gen_pages.py). Any change to a `.md` file
triggers it. Every run uploads the artifact, but only runs on `main` deploy
it. The GitLab `pages` job and the local `post-commit` preview hook call the
same script. `make pages` builds the site with `CI=1`, as the Pages jobs do,
and opens `public/index.html` with `xdg-open` (`XDG_OPEN` picks another
command).

#### Site settings

`gen_pages.py` holds only the page template. `build_pages.sh` passes it
`--config` [`scripts/ci/pages.json`](../../scripts/ci/pages.json), which sets:

| Key                | Meaning                                                                       |
| ------------------ | ----------------------------------------------------------------------------- |
| `title`            | Site name, in the navbar and as the home page title                           |
| `url`              | Public URL for canonical links, `sitemap.xml` and `robots.txt`                |
| `home`             | Markdown file published as `index.html`                                       |
| `image`            | Open Graph preview image, used when a page links it (`null` for none)         |
| `nav`              | Menu sections in order, each a `label` and a `target`                         |
| `nav_labels`       | Menu labels that replace a page's first heading or a directory name           |
| `nav_exclude`      | Pages kept out of the menu (`fnmatch`, `*` also matches `/`), still published |
| `renamed_prefixes` | Source prefixes published under another name                                  |
| `skipped_dirs`     | Directories never scanned when Git is missing                                 |
| `asset_extensions` | Linked files copied into the site instead of pointing to the forge            |

A missing, unknown or mistyped key stops the build with exit code 2.

#### Pages and links

Each page keeps its source path: `dist/arch/install.md` becomes
`dist/arch/install.md/index.html`. The `home` page becomes the site index, and
`.github/` is published as `github/` because `actions/upload-pages-artifact`
drops `.github` from the artifact. A page's title is its first heading, else
its path; the home page takes the site title.

`gen_pages.py` rewrites the `href` and `src` of real `<a>`, `<img>` and
`<source>` tags, so tags shown as code stay as written:

- a link to a Markdown file goes to its page, query and anchor included;
- a link starting with `/` is relative to the repository root, as on the forges;
- a linked image is copied into `public/`, under `github/` for `.github/`;
- a link to any other file or directory goes to the forge's file browser at
  the built commit (`GITHUB_SHA` here, `CI_COMMIT_SHA` on GitLab). The local
  preview links to the file in the checkout instead.

A link to a missing file, or to a heading or anchor its page lacks, fails the
build: `gen_pages.py` lists the broken links on stderr and exits 1. The
`test-gen-pages` pre-commit hook builds the site on every Markdown change, so
they are caught before the commit. Only the `id` and `name` attributes of the
page body count; `id="x"` written in a paragraph does not. Heading ids follow
GitHub: accents stay (`## Présentation` gets `#présentation`), punctuation
goes, each space becomes a hyphen (`## Install & configure` gets
`#install--configure`) and a repeated heading gets `-1`, `-2`. GitLab merges
runs of hyphens, so a link written for GitLab may fail the build.

Fenced code follows CommonMark: backtick or tilde fences, closed by a fence of
the same character at least as long, so a four-backtick fence can show a
three-backtick one. A fence inside a blockquote or an alert is a code block
too. Without Pygments, code renders without highlighting. Each build also
deletes what a previous build left in `public/` for renamed or deleted pages.

#### Menu

A `nav` target is one page, a list of pages shown as a dropdown, or a
directory such as `ansible/`. A directory's dropdown mirrors its tree: its
`README.md` as Overview, its other pages, then one entry per subdirectory. A
subdirectory links its own `README.md`, or shows as a heading without one
(`roles/`), with its pages indented below. A directory with no page and a
single subdirectory is folded into one entry (`a/b`). Labels come from
`nav_labels`, else the page's first heading. A new README in a listed
directory therefore appears without any setting change.

The current section is highlighted, and a submenu of more than ten entries
takes two columns on wide screens. Dropdowns open on hover with a mouse, and
on click on touch screens or in the collapsed menu.

#### SEO and theme

Each `<head>` has a description from the page's first paragraph with text,
cut to 160 characters, Open Graph and Twitter card tags, a canonical URL and
the `og:image`. Every build, the local preview included, writes `sitemap.xml`
and `robots.txt`. Their URLs start with `url`, the GitLab Pages domain
`https://dotfiles.depad.fr/`, where `robots.txt` sits at the root of the
host. The GitHub copy points there too, so search engines index one site, and
`SITE_URL` overrides it. Crawlers ignore `robots.txt` on a project site such
as `<user>.github.io/<repo>/`: submit the sitemap in Google Search Console or
Bing Webmaster Tools instead.

The pages use the Gruvbox colours of the Hyprland desktop: `style.css` takes
its dark background, text and accent from `hyprtoolkit.conf.j2`, and a test
checks they match. The theme menu, last in the navbar, picks Light, Dark or
Auto (the default, which follows the desktop) and saves the choice in
`localStorage`; its button shows a sun, a moon or a half circle. A script in
`<head>` sets `data-theme` on `<html>` before the page is drawn, and Gruvbox
Light applies under `data-theme="light"`. Without JavaScript the site stays
dark. Code uses the Pygments `gruvbox-dark` and `gruvbox-light` styles.

The favicon files (`favicon.ico` at 16, 32 and 48 px, `favicon.png` at 192 px
and `apple-touch-icon.png` at 180 px) sit next to `style.css` in
`scripts/ci/` and are copied to the site root. The CDN stylesheets and
scripts carry Subresource Integrity hashes: `gen_pages.py` builds their tags
from `CDN_INTEGRITY`, which also gives the command to recompute a hash.

`build_pages.sh` fails when the `markdown` module is missing in CI (`CI` is
set) and skips the build only for the local hook.

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
| `gen_pages.py`             | `build_pages.sh`, with the settings of `pages.json`          |

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
