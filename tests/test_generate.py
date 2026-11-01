from pathlib import Path

import pytest

from higgsfield_assets import generate as g


def test_build_arguments_adds_brand_style():
    payload = g.build_arguments("a classroom", "4:3", "2K")
    assert payload["prompt"].startswith("a classroom. ")
    assert "#1A4D6E" in payload["prompt"]
    assert payload["aspect_ratio"] == "4:3"
    assert payload["resolution"] == "2K"


def test_build_arguments_plain():
    assert g.build_arguments("raw", "1:1", "1K", styled=False)["prompt"] == "raw"


def test_extract_urls_handles_nested_shapes():
    result = {
        "images": [{"url": "https://cdn.example/a.png"}, {"url": "https://cdn.example/b.png"}],
        "video": {"url": "https://cdn.example/c.mp4"},
        "note": "not a url",
        "dup": "https://cdn.example/a.png",
    }
    assert g.extract_urls(result) == [
        "https://cdn.example/a.png",
        "https://cdn.example/b.png",
        "https://cdn.example/c.mp4",
    ]


def test_generate_uses_client_and_downloads(monkeypatch, tmp_path):
    calls = {}

    class FakeClient:
        def subscribe(self, model, arguments, on_enqueue, on_queue_update):
            calls["model"] = model
            calls["arguments"] = arguments
            on_enqueue("req-1")
            return {"images": [{"url": "https://cdn.example/hero.png"}]}

    def fake_download(urls, out_dir, stem):
        return [Path(out_dir) / f"{stem}.png" for _ in urls]

    monkeypatch.setattr(g, "download", fake_download)
    saved = g.generate("m/1", {"prompt": "x"}, tmp_path, "hero", client=FakeClient())
    assert calls == {"model": "m/1", "arguments": {"prompt": "x"}}
    assert saved == [tmp_path / "hero.png"]


def test_generate_raises_without_urls(tmp_path):
    class EmptyClient:
        def subscribe(self, *a, **k):
            return {"images": []}

    with pytest.raises(RuntimeError):
        g.generate("m", {}, tmp_path, "x", client=EmptyClient())


def test_dry_run_needs_no_credentials(monkeypatch, capsys):
    for var in ("HF_KEY", "HF_API_KEY", "HF_API_SECRET"):
        monkeypatch.delenv(var, raising=False)
    assert g.main(["--dry-run", "presets", "--only", "hero"]) == 0
    assert '"name": "hero"' in capsys.readouterr().out


def test_missing_credentials_exit_code(monkeypatch):
    for var in ("HF_KEY", "HF_API_KEY", "HF_API_SECRET"):
        monkeypatch.delenv(var, raising=False)
    assert g.main(["presets"]) == 2
