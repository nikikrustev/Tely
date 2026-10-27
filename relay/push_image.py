"""Build the relay image without Docker or ACR Tasks and push it to our ACR.

    python -m relay.push_image                    # from the repo root; az login; prints the image reference
    (needs `pip install uv` on the deploying machine: it resolves the Linux wheels)

WHY (docs/DECISIONS.md D17): the free subscription refuses ACR Tasks ("TasksOperationsNotAllowed", 23 Oct 2026), so azd's
remote build can't run, and A's machine has no Docker. An image is only a base image plus layers, so this script takes
python:3.12-slim (linux/amd64) from Docker Hub, adds ONE layer with the same files relay/Dockerfile copies (the relay,
B's tely package, the four judge-bundle files B's load_bundle reads) plus Linux wheels from pip, and pushes it
with the registry HTTP API. Auth is the signed-in user's own token (`az acr login --expose-token`): no admin password
and no key; the Container App pulls with its managed identity. relay/Dockerfile stays the reference build for anyone
with Docker. The tag is the layer's content hash, so the same inputs give the same tag.
"""
from __future__ import annotations

import base64
import gzip
import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ("registry-1.docker.io", "library/python", "3.12-slim")
REPO = "tely/relay"
JUDGE = "web/public/replay/v1/judge"
BUNDLE_FILES = ["meta.json", "events.jsonl", "signals.json", "ticks.json.gz"]
MANIFEST_TYPES = ", ".join([
    "application/vnd.oci.image.index.v1+json", "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.oci.image.manifest.v1+json", "application/vnd.docker.distribution.manifest.v2+json"])


def sh(*args: str) -> str:
    return subprocess.run(list(args), check=True, capture_output=True, text=True, shell=sys.platform == "win32").stdout


# ---------------------------------------------------------------- registry client (Docker Registry HTTP API v2)
class Registry:
    def __init__(self, host: str, basic: tuple[str, str] | None = None):
        self.host, self.basic, self.tokens = host, basic, {}

    def _token(self, challenge: str, repo: str) -> str:
        parts = dict(p.split("=", 1) for p in challenge[len("Bearer "):].replace('"', "").split(","))
        scope = f"repository:{repo}:pull,push" if self.basic else f"repository:{repo}:pull"
        url = f"{parts['realm']}?service={parts['service']}&scope={scope}"
        req = urllib.request.Request(url)
        if self.basic:
            req.add_header("Authorization", "Basic " + base64.b64encode(":".join(self.basic).encode()).decode())
        body = json.loads(urllib.request.urlopen(req).read())
        return body.get("access_token") or body["token"]

    def call(self, method: str, path: str, repo: str, data: bytes | None = None, headers: dict | None = None,
             absolute: str | None = None):
        url = absolute or f"https://{self.host}/v2/{repo}/{path}"
        for _ in range(2):
            req = urllib.request.Request(url, data=data, method=method, headers=dict(headers or {}))
            if repo in self.tokens:
                req.add_header("Authorization", f"Bearer {self.tokens[repo]}")
            try:
                return urllib.request.urlopen(req)
            except urllib.error.HTTPError as e:
                if e.code == 401 and repo not in self.tokens:
                    self.tokens[repo] = self._token(e.headers["WWW-Authenticate"], repo)
                    continue
                raise
        raise RuntimeError("unauthorised")

    def has_blob(self, repo: str, digest: str) -> bool:
        try:
            self.call("HEAD", f"blobs/{digest}", repo)
            return True
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False
            raise

    def put_blob(self, repo: str, digest: str, data: bytes) -> None:
        if self.has_blob(repo, digest):
            return
        r = self.call("POST", "blobs/uploads/", repo, data=b"")
        loc = r.headers["Location"]
        loc = loc if loc.startswith("http") else f"https://{self.host}{loc}"
        sep = "&" if "?" in loc else "?"
        self.call("PUT", "", repo, data=data, headers={"Content-Type": "application/octet-stream"},
                  absolute=f"{loc}{sep}digest={digest}")


def sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------- the one layer
def wheels(target: Path) -> None:
    """Linux x86_64 wheels for the relay and B's runtime deps (B's pins, read from B's pyproject)."""
    py = tomllib.loads((ROOT / "pipeline" / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    reqs = [*py["dependencies"], *py["optional-dependencies"]["mcp"]]
    reqs += [s.strip() for s in (ROOT / "relay" / "requirements.txt").read_text(encoding="utf-8").splitlines()
             if s.strip() and not s.lstrip().startswith("#")]
    # uv, not pip: pip evaluates markers for the machine it runs on (it pulls pywin32 on Windows); uv resolves for Linux.
    subprocess.run([sys.executable, "-m", "uv", "pip", "install", "--quiet", "--target", str(target),
                    "--python-platform", "x86_64-manylinux_2_28", "--python-version", "3.12", "--only-binary", ":all:",
                    *reqs], check=True)


def app_files() -> list[tuple[Path, str]]:
    out = []
    for base in ("relay", "pipeline/tely"):
        for p in sorted((ROOT / base).rglob("*")):
            rel = p.relative_to(ROOT).as_posix()
            if p.is_file() and "__pycache__" not in rel and not rel.startswith("relay/tests/") and p.suffix != ".pyc":
                out.append((p, rel))
    out.append((ROOT / "pipeline" / "pyproject.toml", "pipeline/pyproject.toml"))
    out += [(ROOT / JUDGE / f, f"{JUDGE}/{f}") for f in BUNDLE_FILES]
    return out


def layer() -> tuple[bytes, str]:
    """(gzipped tar, diff_id). Fixed mtime/owner and sorted names, so the same inputs give the same bytes."""
    raw = io.BytesIO()
    with tempfile.TemporaryDirectory() as tmp, tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as tar:
        site = Path(tmp) / "site"
        wheels(site)
        entries = [(p, f"app/{rel}") for p, rel in app_files()]
        entries += [(p, "app/site/" + p.relative_to(site).as_posix()) for p in sorted(site.rglob("*")) if p.is_file()]
        dirs = sorted({str(Path(n).parent).replace("\\", "/") for _, n in entries})
        seen = set()
        for d in dirs:
            for i in range(1, len(d.split("/")) + 1):
                sub = "/".join(d.split("/")[:i])
                if sub not in seen:
                    seen.add(sub)
                    ti = tarfile.TarInfo(sub)
                    ti.type, ti.mode, ti.mtime = tarfile.DIRTYPE, 0o755, 0
                    tar.addfile(ti)
        for p, name in sorted(entries, key=lambda e: e[1]):
            data = p.read_bytes()
            ti = tarfile.TarInfo(name)
            ti.size, ti.mode, ti.mtime = len(data), 0o644, 0
            tar.addfile(ti, io.BytesIO(data))
    tar_bytes = raw.getvalue()
    return gzip.compress(tar_bytes, compresslevel=6, mtime=0), sha(tar_bytes)


# ---------------------------------------------------------------- build + push
def build_and_push(acr: str) -> str:
    """Build the image and push it to the registry `acr` (login server). Returns the image reference."""
    token = json.loads(sh("az", "acr", "login", "-n", acr.split(".")[0], "--expose-token", "-o", "json"))["accessToken"]
    dst = Registry(acr, ("00000000-0000-0000-0000-000000000000", token))   # the user's own token, never stored
    hub = Registry(BASE[0])

    idx = json.loads(hub.call("GET", f"manifests/{BASE[2]}", BASE[1], headers={"Accept": MANIFEST_TYPES}).read())
    if "manifests" in idx:
        m = next(x for x in idx["manifests"] if x["platform"]["os"] == "linux" and x["platform"]["architecture"] == "amd64")
        man_raw = hub.call("GET", f"manifests/{m['digest']}", BASE[1], headers={"Accept": m["mediaType"]}).read()
    else:
        man_raw = json.dumps(idx).encode()
    man = json.loads(man_raw)
    cfg = json.loads(hub.call("GET", f"blobs/{man['config']['digest']}", BASE[1]).read())
    for lyr in man["layers"]:                                  # copy the base layers into our registry once
        if not dst.has_blob(REPO, lyr["digest"]):
            dst.put_blob(REPO, lyr["digest"], hub.call("GET", f"blobs/{lyr['digest']}", BASE[1]).read())

    gz, diff_id = layer()
    dst.put_blob(REPO, sha(gz), gz)
    oci = man["mediaType"].startswith("application/vnd.oci")
    env = [e for e in cfg["config"].get("Env", []) if not e.startswith("PYTHONPATH=")]
    cfg["config"].update({
        "Env": env + ["PYTHONPATH=/app/site:/app/pipeline:/app", "PYTHONUNBUFFERED=1", "PYTHONDONTWRITEBYTECODE=1"],
        "WorkingDir": "/app", "User": "65534", "ExposedPorts": {"8080/tcp": {}},
        "Entrypoint": None,
        "Cmd": ["python", "-m", "uvicorn", "relay.app:app", "--host", "0.0.0.0", "--port", "8080",
                "--ws-max-size", "65536"]})                  # same as relay/Dockerfile: 64 KB per /voice frame
    cfg["rootfs"]["diff_ids"].append(diff_id)
    cfg.setdefault("history", []).append({"created_by": "relay/push_image.py: app + wheels layer (D17)"})
    cfg_raw = json.dumps(cfg, separators=(",", ":")).encode()
    dst.put_blob(REPO, sha(cfg_raw), cfg_raw)
    man["config"] = {**man["config"], "digest": sha(cfg_raw), "size": len(cfg_raw)}
    man["layers"].append({"mediaType": "application/vnd.oci.image.layer.v1.tar+gzip" if oci else
                          "application/vnd.docker.image.rootfs.diff.tar.gzip", "digest": sha(gz), "size": len(gz)})
    man_out = json.dumps(man, separators=(",", ":")).encode()
    tag = sha(gz)[7:19]
    dst.call("PUT", f"manifests/{tag}", REPO, data=man_out, headers={"Content-Type": man["mediaType"]})
    print(f"layer {len(gz) / 1e6:.1f} MB on {BASE[1]}:{BASE[2]}", file=sys.stderr)
    return f"{acr}/{REPO}:{tag}"


def registry_from_env() -> str:
    acr = os.environ.get("AZURE_CONTAINER_REGISTRY_ENDPOINT") or sh("azd", "env", "get-value",
                                                                     "AZURE_CONTAINER_REGISTRY_ENDPOINT")
    return acr.strip().strip('"')


def main() -> int:
    print(build_and_push(registry_from_env()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
