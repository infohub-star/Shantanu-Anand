"""Generate marketing assets for the Avid Academia site with the Higgsfield Python SDK.

Usage examples:

    # Preview what would be sent (no credentials, no credits used)
    python -m higgsfield_assets.generate presets --dry-run

    # Generate every preset image for the landing page
    python -m higgsfield_assets.generate presets

    # Generate a single image from your own prompt
    python -m higgsfield_assets.generate image --prompt "IELTS speaking practice" --aspect-ratio 4:3

    # Ask the Higgsfield Agent (needs Agent API access) to do a multi-step task
    python -m higgsfield_assets.generate agent "Make a 5s promo clip for an IELTS coaching centre"

Credentials are read from HF_KEY, or HF_API_KEY + HF_API_SECRET (see .env.example).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

DEFAULT_MODEL = "bytedance/seedream/v4/text-to-image"
DEFAULT_OUT_DIR = Path("generated")

# Brand colours taken from the Avid Academia landing page (teal #1A4D6E, orange #F5A623).
BRAND_STYLE = (
    "clean modern educational brand style, deep teal (#1A4D6E) and warm orange (#F5A623) accents, "
    "bright natural light, professional photography, no text, no watermark"
)

PRESETS: Dict[str, Dict[str, Any]] = {
    "hero": {
        "prompt": "Confident young Indian student smiling while studying English with an IELTS "
        "preparation book and laptop in a bright modern classroom",
        "aspect_ratio": "16:9",
    },
    "speaking": {
        "prompt": "One-to-one IELTS speaking practice session between a friendly tutor and a student, "
        "both engaged in conversation at a table",
        "aspect_ratio": "4:3",
    },
    "writing": {
        "prompt": "Close-up of a student writing an IELTS essay on paper with a pen, notes and "
        "a cup of tea on the desk",
        "aspect_ratio": "4:3",
    },
    "success": {
        "prompt": "Happy student holding a passport and acceptance letter at an airport, "
        "celebrating a high IELTS band score",
        "aspect_ratio": "4:3",
    },
}


def build_arguments(prompt: str, aspect_ratio: str, resolution: str, styled: bool = True) -> Dict[str, Any]:
    """Build the request payload sent to the Higgsfield model."""
    full_prompt = f"{prompt}. {BRAND_STYLE}" if styled else prompt
    return {
        "prompt": full_prompt,
        "resolution": resolution,
        "aspect_ratio": aspect_ratio,
        "camera_fixed": False,
    }


def extract_urls(result: Any) -> List[str]:
    """Collect every http(s) URL in a result, whatever its shape (images, video, audio...)."""
    found: List[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, (list, tuple)):
            for value in node:
                walk(value)
        elif isinstance(node, str) and node.startswith(("http://", "https://")):
            if node not in found:
                found.append(node)

    walk(result)
    return found


def download(urls: Iterable[str], out_dir: Path, stem: str) -> List[Path]:
    """Download generated files into out_dir as <stem>.<ext> / <stem>-2.<ext> ..."""
    import httpx

    out_dir.mkdir(parents=True, exist_ok=True)
    saved: List[Path] = []
    for index, url in enumerate(urls, start=1):
        ext = Path(urlparse(url).path).suffix or ".bin"
        name = f"{stem}{ext}" if index == 1 else f"{stem}-{index}{ext}"
        target = out_dir / name
        with httpx.stream("GET", url, follow_redirects=True, timeout=120) as response:
            response.raise_for_status()
            with target.open("wb") as handle:
                for chunk in response.iter_bytes():
                    handle.write(chunk)
        saved.append(target)
    return saved


def has_credentials() -> bool:
    return bool(os.environ.get("HF_KEY") or (os.environ.get("HF_API_KEY") and os.environ.get("HF_API_SECRET")))


def generate(model: str, arguments: Dict[str, Any], out_dir: Path, stem: str, client: Any = None) -> List[Path]:
    """Submit one job, wait for it, and download the outputs."""
    if client is None:
        import higgsfield_client as client  # module-level sync client

    print(f"[{stem}] submitting to {model} ...", flush=True)
    result = client.subscribe(
        model,
        arguments=arguments,
        on_enqueue=lambda request_id: print(f"[{stem}] queued as {request_id}", flush=True),
        on_queue_update=lambda status: print(f"[{stem}] {type(status).__name__}", flush=True),
    )
    urls = extract_urls(result)
    if not urls:
        raise RuntimeError(f"[{stem}] no output URLs in result: {json.dumps(result)[:500]}")
    saved = download(urls, out_dir, stem)
    for path in saved:
        print(f"[{stem}] saved {path}")
    return saved


def run_agent(task: str) -> int:
    from higgsfield_client import SyncClient

    client = SyncClient()
    session = client.agents.sessions.create()
    print(f"agent session: {session.session_id}")
    result = client.agents.sessions.run(
        session.session_id,
        f"{task}. Brand: Avid Academia, English & IELTS coaching. {BRAND_STYLE}.",
        on_question=lambda question: "Use your best judgement; keep it on-brand and professional.",
    )
    print(f"status: {result.status}")
    print(result.text)
    for url in result.asset_urls or []:
        print(url)
    return 0 if result.status == "completed" else 1


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Higgsfield model id (default: {DEFAULT_MODEL})")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR, help="output folder (default: generated/)")
    parser.add_argument("--resolution", default="2K", help="e.g. 1K, 2K, 4K (default: 2K)")
    parser.add_argument("--dry-run", action="store_true", help="print the payloads only; uses no credits")
    sub = parser.add_subparsers(dest="command", required=True)

    presets = sub.add_parser("presets", help="generate the landing-page preset images")
    presets.add_argument("--only", nargs="+", choices=sorted(PRESETS), help="generate only these presets")

    image = sub.add_parser("image", help="generate one image from a custom prompt")
    image.add_argument("--prompt", required=True)
    image.add_argument("--aspect-ratio", default="16:9")
    image.add_argument("--name", default="custom", help="output file name (without extension)")
    image.add_argument("--no-brand-style", action="store_true", help="send the prompt exactly as written")

    agent = sub.add_parser("agent", help="run a multi-step task with the Higgsfield Agent API")
    agent.add_argument("task")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    if args.command == "presets":
        names = args.only or list(PRESETS)
        jobs = [(n, build_arguments(PRESETS[n]["prompt"], PRESETS[n]["aspect_ratio"], args.resolution)) for n in names]
    elif args.command == "image":
        jobs = [(args.name, build_arguments(args.prompt, args.aspect_ratio, args.resolution, not args.no_brand_style))]
    else:
        jobs = []

    if args.dry_run:
        if args.command == "agent":
            print(json.dumps({"agent_task": args.task}, indent=2))
        for name, payload in jobs:
            print(json.dumps({"name": name, "model": args.model, "arguments": payload}, indent=2))
        return 0

    if not has_credentials():
        print("Missing credentials: set HF_KEY or HF_API_KEY + HF_API_SECRET (see .env.example).", file=sys.stderr)
        return 2

    if args.command == "agent":
        return run_agent(args.task)

    failures = 0
    for name, payload in jobs:
        try:
            generate(args.model, payload, args.out, name)
        except Exception as exc:  # keep going with the other presets
            failures += 1
            print(f"[{name}] failed: {exc}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
