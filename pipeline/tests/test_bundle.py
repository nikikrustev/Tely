# build_bundle + hosting config checks. No Azure, no TTS, no Bicep CLI: CI-safe.
import gzip
import hashlib
import json
import re
import shutil
from pathlib import Path

import pytest

from tely import build_bundle
from tely.commentary import planner
from tely.commentary.source import MATCH_DIRS
from tely.spoiler import OUTCOME

ROOT = Path(__file__).resolve().parents[2]


class FakeSynth:
    def synthesise(self, doc):
        text = re.sub(r"<[^>]+>|\[\w+\]", "", doc)
        return b"ID3fake", planner.estimate(text, "", 0) * 1.15


def no_segments(cut, out):
    return "skipped: test"


@pytest.fixture()
def bundle_dir(tmp_path):
    """A copy of B's judge-cut match files, as build_match would leave them."""
    for name in ("meta.json", "events.jsonl", "signals.json", "ticks.json.gz"):
        shutil.copyfile(MATCH_DIRS["judge"] / name, tmp_path / name)
    return tmp_path


def build(out, run_match=lambda cut, out: None, run_segments=no_segments):
    return build_bundle.build("judge", out, lambda: FakeSynth(), run_match=run_match, run_segments=run_segments)


def test_manifest_hashes_every_file_and_carries_the_notice(bundle_dir):
    rep = build(bundle_dir)
    man = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    on_disk = {p.relative_to(bundle_dir).as_posix() for p in bundle_dir.rglob("*") if p.is_file()} - {"manifest.json"}
    assert set(man["sha256"]) == on_disk and man["files"] == len(on_disk) == rep["files"]
    for rel, digest in man["sha256"].items():
        assert hashlib.sha256((bundle_dir / rel).read_bytes()).hexdigest() == digest
    assert man["ai_voice_notice"] == "Commentary uses Azure AI voices. Match data is synthetic."
    assert man["tracks"] == {"en": {"radio": "cues.en.radio.jsonl"}} and man["delay_s"] == 10.0
    assert man["segments"] is None  # B's Stage 2 isn't there: no segments, and no cues merged anywhere


def test_chapters_are_spoiler_safe(bundle_dir):
    build(bundle_dir)
    man = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    cues = [json.loads(s) for s in (bundle_dir / "cues.en.radio.jsonl").read_text(encoding="utf-8").splitlines()]
    builds = [c for c in cues if c["kind"] == "build"]
    assert len(man["chapters"]) >= len(builds) >= 1
    for i, ch in enumerate(man["chapters"], 1):
        assert ch["label"] == f"Big moment {i}"  # never "goal" or "save"
        assert not set(ch["label"].lower().split()) & OUTCOME
    for c in builds:  # each build-up is reachable from a chapter that starts before it
        assert any(ch["t"] <= c["t_in"] <= ch["t"] + build_bundle.CHAPTER_LEAD_S for ch in man["chapters"])


def test_manifest_is_deterministic(bundle_dir):
    build(bundle_dir)
    first = (bundle_dir / "manifest.json").read_bytes()
    build(bundle_dir)
    assert (bundle_dir / "manifest.json").read_bytes() == first and b"\r" not in first


def test_recompressed_gzip_is_restored_not_flagged(bundle_dir):
    original = (bundle_dir / "ticks.json.gz").read_bytes()

    def recompress(cut, out):  # same data, different gzip bytes (another zlib build)
        (out / "ticks.json.gz").write_bytes(gzip.compress(gzip.decompress(original), compresslevel=1, mtime=0))

    build(bundle_dir, run_match=recompress)
    assert (bundle_dir / "ticks.json.gz").read_bytes() == original


def test_changed_b_content_is_a_determinism_error(bundle_dir):
    def drift(cut, out):
        p = out / "events.jsonl"
        p.write_bytes(p.read_bytes() + b"\n")

    with pytest.raises(build_bundle.DeterminismError, match="events.jsonl"):
        build(bundle_dir, run_match=drift)


def test_segments_listed_once_b_builds_them(bundle_dir):
    def segments(cut, out):
        (out / "segments.json").write_text("[]\n", encoding="utf-8")
        return "built"

    rep = build(bundle_dir, run_segments=segments)
    man = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    assert rep["segments"] == "built" and man["segments"] == "segments.json"


def test_size_limit(bundle_dir, monkeypatch):
    monkeypatch.setattr(build_bundle, "MAX_BYTES", 1000)
    with pytest.raises(RuntimeError, match="too big"):
        build(bundle_dir)


# --- hosting config (static checks; the Bicep compile needs the Bicep CLI, which CI doesn't have) ----------------

def test_staticwebapp_config_mime_types_and_caching():
    cfg = json.loads((ROOT / "web" / "staticwebapp.config.json").read_text(encoding="utf-8"))
    assert {".jsonl", ".gz", ".mp3", ".vtt"} <= set(cfg["mimeTypes"])
    assert cfg["mimeTypes"][".gz"] == "application/gzip"  # raw gzip bytes; the browser decompresses ticks itself
    immutable = [r["route"] for r in cfg["routes"] if "immutable" in r["headers"]["Cache-Control"]]
    assert immutable == ["/replay/v1/judge/audio/*", "/assets/*"]  # only hash-named files; cues get rebuilt in place
    assert "/replay/*" in cfg["navigationFallback"]["exclude"]


def test_bicep_is_static_web_apps_free_only():
    main = (ROOT / "infra" / "main.bicep").read_text(encoding="utf-8")
    web = (ROOT / "infra" / "web.bicep").read_text(encoding="utf-8")
    assert "@allowed(['Free'])" in main  # D6: no money
    assert "Microsoft.Web/staticSites@" in web and "'azd-service-name': 'web'" in main
    resources = re.findall(r"^resource \w+ '([^@']+)@", main + "\n" + web, flags=re.M)
    assert sorted(resources) == ["Microsoft.Resources/resourceGroups", "Microsoft.Web/staticSites"]
    assert not re.search(r"(?i)listKeys|apiKey|secret", main + web)


def test_azure_yaml_ships_the_swa_config():
    text = (ROOT / "azure.yaml").read_text(encoding="utf-8")
    assert "host: staticwebapp" in text and "dist: dist" in text and "path: infra" in text
    assert text.count("staticwebapp.config.json dist/") == 2  # posix and windows hooks
