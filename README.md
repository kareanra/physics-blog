# Computational Physics Notes

A Quarto blog where each post is a worked derivation paired with runnable code.
Every figure is generated at render time, so the plots match the
equations by construction.

## You do not need Quarto installed locally

The site is rendered in the cloud. There are three ways to work with it, none of
which require Quarto on your own machine.

### 1. Publish by pushing (no local tooling)

The `.github/workflows/publish.yml` workflow installs Quarto and Python in CI,
runs `quarto render`, and deploys to GitHub Pages on every push to `main`. To go
live: create the repo, set **Settings -> Pages -> Source: GitHub Actions**, and
push. The site builds and deploys automatically to
`https://kareanra.github.io/physics-blog`.

### 2. Preview a change before it merges (no local tooling)

Open a pull request against `main`. The `.github/workflows/preview.yml` workflow
renders the site and attaches it as a downloadable artifact (`site-preview`) on
the workflow run. Download it and open `index.html` to review, or just merge and
check the live site.

### 3. Live preview in the browser via Codespaces

The `.devcontainer/` config gives a cloud dev environment with Quarto, Python,
and the dependencies preinstalled. On GitHub, click **Code -> Codespaces ->
Create codespace on main**, wait for it to build, then in its terminal run:

```bash
quarto preview
```

Port 4200 forwards automatically and opens a live-reloading preview in your
browser. Nothing is installed on your own computer.

## Local preview (optional, only if you do install Quarto)

```bash
pip install -r requirements.txt      # numpy, scipy, matplotlib, jupyter
quarto preview                       # live reload at http://localhost:4200
```

## Structure

```
_quarto.yml                      site + build config (execute-dir: project)
dslit.py                         consolidated physics module imported by all posts
index.qmd                        blog listing
about.qmd                        about page
posts/_metadata.yml              shared post settings (code-fold, freeze)
posts/double-slit-part1/         part 1: kernel + slit transmission
.devcontainer/devcontainer.json  Codespaces env with Quarto + Python preinstalled
.github/workflows/publish.yml    render + deploy to GitHub Pages on push to main
.github/workflows/preview.yml    render a PR into a downloadable artifact
```
