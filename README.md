# Computational Physics Notes
 
**Live site:** [areanraines.com](https://areanraines.com)
 
A Quarto blog where each post is a worked physics derivation paired with runnable
Python code. Every figure is generated at render time, so the plots match the
equations by construction. Backed by a small serverless AWS system that handles
email subscriptions and scheduled weekly newsletter delivery.
 
## Technologies
 
**Content and publishing**
- [Quarto](https://quarto.org) — static site generator with executable code blocks
- Python (numpy, scipy, matplotlib) — physics simulations and figure generation
- GitHub Pages — hosting, with a custom domain via CNAME
**CI/CD and developer environment**
- GitHub Actions — publish on push to `main`; PR preview builds attached as downloadable artifacts
- Dev Container / Codespaces — cloud dev environment with Quarto and Python preinstalled, so contributors need nothing installed locally
**Email newsletter backend** (in [`infra/`](infra/))
- AWS CDK — infrastructure as code
- API Gateway — subscribe / unsubscribe REST endpoints
- Lambda — subscription handlers and newsletter dispatch
- DynamoDB — subscriber storage
- SES — transactional and bulk email delivery
- EventBridge — weekly scheduled trigger for newsletter dispatch

## You do not need Quarto installed locally
 
The site is rendered in the cloud. There are three ways to work with it, none of
which require Quarto on your own machine.
 
### 1. Publish by pushing (no local tooling)
 
The `.github/workflows/publish.yml` workflow installs Quarto and Python in CI,
runs `quarto render`, and deploys to GitHub Pages on every push to `main`. To go
live: create the repo, set **Settings → Pages → Source: GitHub Actions**, and
push. The site builds and deploys automatically to `https://kareanra.github.io/physics-blog`.
 
### 2. Preview a change before it merges (no local tooling)
 
Open a pull request against `main`. The `.github/workflows/preview.yml` workflow
renders the site and attaches it as a downloadable artifact (`site-preview`) on
the workflow run. Download it and open `index.html` to review.

## Structure
 
```
_quarto.yml                      site + build config (execute-dir: project)
dslit.py                         consolidated physics module imported by all posts
index.qmd                        blog listing
about.qmd                        about page
subscribe-form.html              email-signup widget, present on every page via include-after-body
posts/_metadata.yml              shared post settings
posts/                           individual blog posts
.devcontainer/devcontainer.json  Codespaces env with Quarto + Python preinstalled
.github/workflows/publish.yml    render + deploy to GitHub Pages on push to main
.github/workflows/preview.yml    render a PR into a downloadable artifact
infra/                           AWS CDK app for the email newsletter backend (SES/Lambda/DynamoDB/API Gateway/EventBridge)
```
 
## Email newsletter
 
Readers can subscribe via the form on every page (`subscribe-form.html`) and
get a weekly email when there's a new post, sent through Amazon SES. The
backend (Lambda, DynamoDB, API Gateway, EventBridge schedule) is a separate
CDK app, deployed independently of this repo's GitHub Pages publish workflow.
