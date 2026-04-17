# ArxivFilterPro

ArxivFilterPro is a daily arXiv monitoring pipeline. It fetches recently updated papers from selected categories, filters them with a configurable keyword logic, generates structured summaries, publishes card-style pages to a GitHub Pages site, and sends one daily digest email.

## What It Does

- Fetches arXiv papers updated in the last 24 hours, including version updates such as `v2`
- Filters papers with a configurable boolean keyword expression
- Generates structured paper outputs under `data/<arxiv_id_with_version>/`
- Builds a static website in `site/` with searchable paper cards and detail views
- Sends a daily summary email for newly published site entries

## Setup

```bash
pip install -r requirements.txt
cp config_template.yaml config.yaml
```

Edit `config.yaml` and set the required values:

- `categories`
- `keyword_logic`
- `sites.local_path`
- `sites.public_url`
- `mail.*`
- `codex.*`

## Run

Normal run:

```bash
./run.sh
```

Test mode:

```bash
./run.sh --test-mode
```

## Outputs

For each processed paper, the pipeline writes a directory under `data/` containing:

- `metadata.json`
- `paper.pdf`
- `title_zh.md`
- `abstract.md`
- `ai_abstract.md`
- `problem.md`
- `method.md`
- `result.md`
- `keypoint.md`
- `content.md`

The website is generated under `site/`. Historical published paper IDs are recorded in `previous_arxivs.csv`.

## Deployment

Use `site/` as a separate GitHub Pages repository working tree. Configure GitHub Pages to deploy from the `main` branch at repository root. After each push to that branch, GitHub Pages will redeploy the site automatically.

## Notes

- The pipeline only accepts versioned arXiv IDs such as `2503.00001v1`
- Test mode can use a single target paper
- Site content supports Markdown and basic LaTeX rendering
