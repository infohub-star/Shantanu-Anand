# Avid Academia — Higgsfield asset generator

Generates on-brand images (and, via the Agent API, videos) for the Avid Academia
English & IELTS coaching landing page using the official
[Higgsfield Python SDK](https://github.com/higgsfield-ai/higgsfield-client) (`higgsfield-client`, Apache-2.0).

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env          # fill in your key from https://cloud.higgsfield.ai/
export $(grep -v '^#' .env | xargs)
```

Every real generation uses Higgsfield credits. `--dry-run` uses none.

## Usage

```bash
# See exactly what will be sent (no key needed, no credits)
python -m higgsfield_assets.generate --dry-run presets

# Generate the landing-page images: hero, speaking, writing, success
python -m higgsfield_assets.generate presets
python -m higgsfield_assets.generate presets --only hero

# One custom image
python -m higgsfield_assets.generate image --prompt "IELTS listening class with headphones" --aspect-ratio 4:3 --name listening

# Multi-step task with the Higgsfield Agent (needs Agent API access on your account)
python -m higgsfield_assets.generate agent "Create a 5 second promo video for the hero section"
```

Files are saved to `generated/` (git-ignored). Use `--model <id>` to pick another
Higgsfield model, `--resolution 4K` for larger output, `--out <dir>` to change the folder.
Every prompt gets the site's teal `#1A4D6E` / orange `#F5A623` style appended automatically; turn this off with `--no-brand-style`.

## SDK capabilities used

| Feature | SDK call |
|---|---|
| Submit a job and wait for it | `higgsfield_client.subscribe(model, arguments=...)` |
| Queue / progress callbacks | `on_enqueue`, `on_queue_update` |
| Agent sessions (multi-step creative tasks) | `SyncClient().agents.sessions.create()` / `.run()` |

The SDK also supports async (`subscribe_async`), webhooks, `status` / `result` / `cancel`
by request id, and uploading reference images (`upload_file`).

## Tests

```bash
pip install pytest && python -m pytest -q
```
