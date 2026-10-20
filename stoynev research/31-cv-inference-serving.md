# 31 — Serving the CV model: RF-DETR export (ONNX/TensorRT), Azure GPU hosting, throughput and cold start

_Accessed/compiled: 20 Oct 2026 · Priority area: TwinCast CV loop (Ingest from video), hosting on Azure, cost and demo reliability_

## TL;DR

- **Export RF-DETR to ONNX and serve it with ONNX Runtime (CUDA EP, CPU fallback).** Use `model.export(format="onnx")` from `rfdetr` 1.11.2. A TensorRT engine (`format="tensorrt"`, FP16 by default) is optional and must be built on the same GPU family it runs on. **`optimize_for_inference()` no longer exists.** It was renamed `inference()` in 1.9.0 and removed in 1.11.0.
- **The GPU is not the bottleneck for a 3-minute clip.** Sourced T4 model-only latencies for RF-DETR-S (3.5 to 5.3 ms) put 4,500 frames at about 16 to 24 s of GPU time. On CPU it takes about 27 to 28 min, based on the only sourced CPU figure (357 to 377 ms per frame on a shared Colab vCPU). Cold start, which the tutorial says can be "up to five minutes", and video decode will dominate.
- **Run batch, then replay.** Process the hero clip with an **ACA job on a serverless T4** (per-second billing, scale to zero). Write detections JSONL to Blob and replay it in sync with the match clock (research 21 replay mode). Claim real-time 25 fps only if we measure it end-to-end. With 6-tile ball slicing, model time alone is about 32 ms of the 40 ms frame budget.
- **Cost is cents per run, but vCPU and RAM cost more than the GPU.** The ACA GPU meter is $0.000095/s in Sweden Central and West Europe, "in addition to" active vCPU and memory. A 10-minute job at 8 vCPU / 56 GiB costs about $0.35. A GPU app left on with `minReplicas: 1` for 21 days costs about $1,072, so never leave it on.
- **Pin the CUDA 12 stack.** ACA serverless GPU currently runs NVIDIA driver 570 with CUDA 12.x, and 580 / 13.x is rolling out. `onnxruntime-gpu` 1.27 and later defaults to CUDA 13, which needs driver 580 or newer. Pin `onnxruntime-gpu==1.26.*` (CUDA 12.8, cuDNN 9) on `nvidia/cuda:12.8.1-cudnn-runtime-ubuntu24.04`. Check `get_providers()` at startup, because ORT quietly falls back to CPU.

## Findings

### 1. Export path: RF-DETR → ONNX → (optional) TensorRT

| Step | What the docs say |
|---|---|
| Install | `pip install "rfdetr[onnx]"` for ONNX, `rfdetr[tensorrt]` for TensorRT. The TensorRT extra brings `tensorrt`, `polygraphy`, `onnxconverter-common` and `onnxruntime-gpu`, and "no `trtexec` binary needed". Current PyPI version: **1.11.2** |
| ONNX export | `model.export()` writes ONNX by default. Parameters: `opset_version=17`, `shape=(h, w)` (each side divisible by `patch_size*num_windows`, which is 32 for Small), `batch_size=1`, `dynamic_batch`, `output_dir`, `output_name`, `notes` |
| Outputs | Raw tensors `dets` (normalised cxcywh) and `labels` (un-activated logits). You must apply a **sigmoid, not a softmax**, drop the background slot (index `-1` for fine-tuned checkpoints with contiguous IDs), and **match outputs by name**. Matching by shape swaps boxes and logits when `num_classes == 3` |
| Resize | Bilinear, half-pixel, **no antialias**, stretched (no letterbox), then ImageNet mean/std. `cv2.resize(..., INTER_LINEAR)` matches this convention |
| TensorRT | `model.export(format="tensorrt")` gives `*_fp16.trt` (`fp16=True` is the default). `dynamic_batch=True, batch_size=opt, max_batch_size=N` builds one optimisation profile. By default the engine is "locked to the GPU architecture and TensorRT version" that built it. `trt_timing_cache` cut rebuild time by 74-76% in their FP16 tests |
| INT8 | On a T4, detection INT8 is only **1.09-1.30× faster** than FP16 and loses 0.5-0.8 AP. It needs calibration images from our own domain (synthetic renders are in-domain for us). **Not worth it for the demo** |
| PyTorch path | `model.inference(compile_backend="cudagraph", batch_size=1, dtype="float16")`. On an L4, RF-DETR-S end-to-end was 5.59 ms with CUDA Graph against 19.88 ms for plain `predict()`, but this path needs torch in the image |

**Raw `trtexec` (alternative):** NVIDIA's trtexec README shows `--onnx`, `--saveEngine`, `--minShapes/--optShapes/--maxShapes` and `--stronglyTyped`. The TensorRT 10.x reference lists `--fp16`. The rf-detr docs say **TensorRT 11 removed the FP16 builder flag**: you feed an FP16-cast graph instead. So on TensorRT 11, use rf-detr's exporter, not `trtexec --fp16`.

### 2. Sourced latencies (compare only like with like)

| Source | Hardware / scope | RF-DETR-S | RF-DETR-M |
|---|---|---|---|
| README / benchmarks | T4, TensorRT 10.4, FP16, batch 1, **model only**, 200 ms gap between passes | 3.5 ms | 4.4 ms |
| TensorRT export doc | T4, TensorRT 10.16, FP16, GPU time per image, plain call | 5.314 ms (b1), 5.334 (b4), 5.482 (b8) | 6.706 ms (b1) |
| CUDA cookbook | **L4** (not a T4), forward / **end-to-end**, b1 | ORT CUDA EP 7.35 / 13.78 ms. Raw `.trt` 2.16 / 9.82 ms. `inference-models` TensorRT 3.41 ms e2e | – |
| CPU cookbook | Shared Colab x86 vCPU, e2e, b1 (they say "pending a rerun") | 357-377 ms (2.7-2.8 FPS). ONNX INT8 is about 1.4× faster on CPU at −2.67 mAP | – |

The rf-detr docs warn: "Never compare milliseconds across these three without checking hardware, precision, batch size, and scope". On a T4, larger batches do **not** lower per-image FP16 time (5.31 → 5.48 ms), so batch 1 is fine. We found **no sourced T4 end-to-end figure** and no T4 ORT CUDA EP figure, so we measure those ourselves.

### 3. Throughput math: 3-minute hero clip

3 min × 60 s × 25 fps = **4,500 frames**. The real-time budget is 1000 / 25 = **40 ms per frame**.

| Per-frame latency (source) | Arithmetic | Total |
|---|---|---|
| 3.5 ms (T4 README, model only) | 4,500 × 3.5 ms | 15.8 s |
| 5.314 ms (T4 TensorRT doc, b1) | 4,500 × 5.314 ms | 23.9 s |
| 6.706 ms (T4, RF-DETR-M) | 4,500 × 6.706 ms | 30.2 s |
| 13.78 ms (L4, ORT CUDA EP, e2e, as a proxy) | 4,500 × 13.78 ms | 62.0 s |
| 357-377 ms (x86 vCPU, e2e) | 4,500 × 0.357-0.377 s | 1,607-1,697 s ≈ **27-28 min** |
| Ball pass with `InferenceSlicer` at 640×640 on 1920×1080: ceil(1920/640) × ceil(1080/640) = 3 × 2 = 6 tiles | 6 × 5.314 ms | **31.9 ms per frame** (80% of the 40 ms budget, before decode and tracking) |

### 4. Hosting options compared

| Option | Scale to zero | Billing (sourced) | Fit |
|---|---|---|---|
| **ACA serverless GPU job** (`Consumption-GPU-NC8as-T4`, "Up to 8 vCPUs, 56 GiB") | Yes. A job runs and stops | T4 $0.000095/s (Sweden Central, West Europe), $0.000073/s (East US), plus active vCPU $0.000034/s and memory $0.000004/GiB-s (West Europe). No GPU idle rate is listed | **Best for batch.** `az containerapp job create --workload-profile-name ...` is a documented parameter. The GPU overview covers "apps and jobs", but we found no GPU-job walkthrough (unverified end-to-end) |
| ACA serverless GPU app | Yes (`minReplicas: 0`), with cold start | Same meters, billed while a replica runs | Live `/detect` endpoint. Only one container per app gets the GPU. Fractional GPUs are not supported |
| Azure ML managed online endpoint | **No** ("Scaling compute to zero: No") | VM price per instance. NC4as_T4_v3 Linux is $0.558/h in Sweden Central. Some SKUs reserve 20% extra quota | Overkill. Costs money all the time |
| Azure ML batch endpoint | Yes (cluster) | Per job. Low-priority compute is allowed (NC4as_T4_v3 Low Priority $0.112/h) | Good for many files. More setup (scoring script, Entra auth, cluster) |
| CPU only (ACA Consumption) | Yes | Normal vCPU and memory meters | Fallback. About 27-28 min per clip (sourced figure above), which is fine for an overnight re-run |
| Roboflow Inference server | n/a | Self-hosted inference "does not use credits" | Core is **Apache-2.0**. `inference/enterprise/` is under the Roboflow Enterprise License, and each model keeps its own licence. GPU image `roboflow-inference-server-gpu:latest` is **10.26 GB** compressed (CPU image 2.47 GB), which is bad for cold start |

**Quota:** create the workload-profiles environment first. Then go to Environment → Settings → **Quota** → "Managed environment consumption T4 GPUs" → New limit → Submit. EA and pay-as-you-go subscriptions have T4 quota by default.

### 5. Cold start: what helps

1. **Small image.** The docs say to remove "development tools and dependencies only required for model development". Compressed sizes on Docker Hub (amd64): `nvidia/cuda:12.8.1-base` 0.10 GB, `-runtime` 2.16 GB, `-cudnn-runtime` 2.86 GB, `-cudnn-devel` 5.87 GB. Keep torch and rfdetr **out** of the serving image: export on a dev box, ship only the `.onnx` file. The `onnxruntime-gpu` 1.26 wheel is 277 MB.
2. **Same-region ACR.** "Avoid far away image registries."
3. **Model in the image vs a mount.** The docs recommend storage mounts for large files "like large language models". Our engine is tens of MB (T4 RF-DETR-S FP16 engine: 59-61 MB), so **bake it into the image**. Use an Azure Files mount only to persist an ORT TensorRT engine cache. TensorRT EP's first build "can be very slow". ORT's own Stable Diffusion example took 384 s to build with no cache and 9 s with an engine cache.
4. **Startup probes.** Use a custom liveness probe or "listen early", so a slow GPU init isn't killed.
5. **Proactive wake.** Start the job or ping the app before judging starts.
6. **Artifact streaming** (ACR **Premium only**, still **preview**, Linux amd64 only). The docs frame it around AKS and claim "over 15%" faster pod readiness, "especially helpful for images that are larger than 30 GB". For a ~3 GB image the gain is unproven, and Premium costs $1.6666/day against Basic's $0.1666 (+$31.50 over 21 days). **Skip it unless measured cold start hurts.**
7. **`minReplicas: 1`** removes cold start but bills GPU, vCPU and RAM every second (see cost below). Use it only during a scheduled live-judging window.

### 6. Cost arithmetic (West Europe list prices, from the Retail Prices API)

- Per second at 8 vCPU / 56 GiB: 0.000095 + 8 × 0.000034 + 56 × 0.000004 = 0.000095 + 0.000272 + 0.000224 = **$0.000591/s** ($2.13/h).
- At 4 vCPU / 16 GiB (requesting less than the profile maximum is shown in community examples; the allowed minimum is unverified): 0.000095 + 0.000136 + 0.000064 = **$0.000295/s**.
- **One batch job, assumed 600 s wall time** (start-up plus decode plus inference; we measure the real figure): 600 × 0.000591 = **$0.35**, or 600 × 0.000295 = $0.18. The GPU share alone is $0.057.
- Free monthly grant: 180,000 vCPU-s / 360,000 GiB-s. Whether it applies to GPU-profile replicas is (unverified). At 8 vCPU / 56 GiB the memory grant runs out after 360,000 / (56 × 600) ≈ 10 runs.
- **Always-on app**, 21 days = 1,814,400 s: × 0.000591 = **$1,072**, or × 0.000295 = $535. The GPU share alone is $172.
- Azure ML online endpoint, NC4as_T4_v3, 504 h × $0.558 = **$281** (it cannot scale to zero).

## So what for us

- **Stages:** Ingest (video → detections → tracks → events), and Truth-check (CV-vs-sim grading). **Helps:** A TwinCast (core), B Speed Trap (speeds come from tracks), E Realism Bench (CV scores), and D Chalk Talk (shares the homography).
- **Recommendation:**
  1. Fine-tune RF-DETR-S (Apache-2.0). Export ONNX on the dev box with `dynamic_batch=True` and `notes={dataset, classes}`.
  2. Serve with ORT 1.26 + CUDA EP (TensorRT EP is optional, with its engine cache on Azure Files) in a CUDA 12.8 cuDNN runtime image of about 3 GB.
  3. Run it as a **Manual ACA job on `Consumption-GPU-NC8as-T4`** in Sweden Central or West Europe. Request quota on day 1.
  4. The job writes `detections.jsonl` (frame, `t_ms`, boxes), plus a stats line with the measured fps and the active providers, to Blob. `trackers` and the events logic run downstream on CPU.
  5. Judges see **replay mode** (research 21) with an honest label: "CV ran as a batch job on a serverless T4 at X fps (measured)". A "Re-run CV" button may start the job and show progress. Don't promise real-time unless our own T4 measurement of decode, detection, tiling and tracking stays under 40 ms per frame.
  6. CPU fallback: the same image without a GPU (ORT falls back to CPU). It takes about 27-28 min per clip, so it's only an emergency path.

## Reuse: code & links

**1. Export (dev box with torch; not in the serving image)**

```python
# pip install "rfdetr[onnx]==1.11.2"        (add [tensorrt] only on a T4 box)
from rfdetr import RFDETRSmall
model = RFDETRSmall(pretrain_weights="checkpoints/twincast_best.pth")
model.export(format="onnx", output_dir="artifacts", output_name="twincast-s",
             dynamic_batch=True, batch_size=1, opset_version=17,
             notes={"dataset": "twincast-v3", "classes": ["player", "goalkeeper", "referee", "ball"]})
# Optional, ON A T4 (engine is GPU-arch + TensorRT-version locked):
# model.export(format="tensorrt", output_dir="artifacts", output_name="twincast-s_t4",
#              dynamic_batch=True, batch_size=1, max_batch_size=8,
#              trt_metadata=True, trt_timing_cache="artifacts/t4.cache")
# TensorRT 10.x CLI equivalent (input tensor is named "input"):
# trtexec --onnx=artifacts/twincast-s.onnx --saveEngine=artifacts/twincast-s_fp16.trt --fp16 \
#   --minShapes=input:1x3xHxW --optShapes=input:1x3xHxW --maxShapes=input:8x3xHxW
```

**2. `detector.py`: ONNX Runtime with TensorRT/CUDA EP and CPU fallback, plus rf-detr decoding**

```python
import os, numpy as np, cv2, onnxruntime as ort

MEAN = np.array([0.485, 0.456, 0.406], np.float32)
STD = np.array([0.229, 0.224, 0.225], np.float32)

def make_session(path: str, use_trt: bool = False, trt_cache: str = "/mnt/trtcache"):
    try:
        ort.preload_dlls()  # ORT >= 1.21: loads CUDA/cuDNN from NVIDIA pip wheels if present
    except Exception:
        pass
    wanted = []
    if use_trt:
        wanted.append(("TensorrtExecutionProvider", {"trt_fp16_enable": True,
                       "trt_engine_cache_enable": True, "trt_engine_cache_path": trt_cache,
                       "trt_timing_cache_enable": True}))
    wanted += [("CUDAExecutionProvider", {"device_id": 0}), "CPUExecutionProvider"]
    avail = set(ort.get_available_providers())
    providers = [p for p in wanted if (p[0] if isinstance(p, tuple) else p) in avail]
    sess = ort.InferenceSession(path, providers=providers)
    active = sess.get_providers()                      # what ORT ACTUALLY enabled
    if os.getenv("REQUIRE_GPU") == "1" and "CUDAExecutionProvider" not in active \
            and "TensorrtExecutionProvider" not in active:
        raise RuntimeError(f"GPU provider failed to load, active={active}")  # ORT falls back silently
    return sess, active

class Detector:
    def __init__(self, sess, background_class_id=-1, threshold=0.4):
        self.sess, self.bg, self.th = sess, background_class_id, threshold
        self.h, self.w = [int(d) for d in sess.get_inputs()[0].shape[2:4]]
        names = [o.name for o in sess.get_outputs()]
        self.i_box = next(i for i, n in enumerate(names) if "dets" in n)    # match by NAME
        self.i_log = next(i for i, n in enumerate(names) if "labels" in n)

    def __call__(self, frames_bgr):                     # list of HxWx3 uint8
        x = np.stack([cv2.resize(cv2.cvtColor(f, cv2.COLOR_BGR2RGB), (self.w, self.h),
                                 interpolation=cv2.INTER_LINEAR) for f in frames_bgr])
        x = ((x.astype(np.float32) / 255.0 - MEAN) / STD).transpose(0, 3, 1, 2).copy()
        out = self.sess.run(None, {self.sess.get_inputs()[0].name: x})
        results = []
        for k, f in enumerate(frames_bgr):
            boxes, logits = out[self.i_box][k], out[self.i_log][k]
            slots = np.arange(logits.shape[-1])
            if self.bg is not None:
                keep_slot = slots != (self.bg % logits.shape[-1])
                logits, slots = logits[:, keep_slot], slots[keep_slot]
            p = 1.0 / (1.0 + np.exp(-np.clip(logits, -88, 88)))       # sigmoid, not softmax
            score, cls = p.max(-1), slots[p.argmax(-1)]
            m = score > self.th
            cx, cy, bw, bh = boxes[m].T
            H, W = f.shape[:2]
            xyxy = np.stack([(cx - bw / 2) * W, (cy - bh / 2) * H, (cx + bw / 2) * W, (cy + bh / 2) * H], 1)
            results.append((xyxy.round(1), score[m].round(3), cls[m]))
        return results
```

**3. `job.py`: ACA job entrypoint (Blob video in, detections JSONL out, managed identity)**

```python
import os, json, time, tempfile, cv2
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from detector import make_session, Detector

acct, cont = os.environ["STORAGE_ACCOUNT_URL"], os.environ.get("CONTAINER", "matches")
svc = BlobServiceClient(acct, credential=DefaultAzureCredential())
tmp = tempfile.mkdtemp()
src, dst = os.path.join(tmp, "in.mp4"), os.path.join(tmp, "detections.jsonl")
with open(src, "wb") as fh:
    svc.get_blob_client(cont, os.environ["VIDEO_BLOB"]).download_blob().readinto(fh)

sess, providers = make_session("/app/model.onnx", use_trt=os.getenv("USE_TRT") == "1")
det, batch = Detector(sess), int(os.getenv("BATCH", "1"))
cap = cv2.VideoCapture(src); fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
t0, n, buf = time.perf_counter(), 0, []
with open(dst, "w") as out:
    def flush():
        global n
        for frame_i, (xyxy, sc, cl) in zip(range(n, n + len(buf)), det(buf)):
            out.write(json.dumps({"frame": frame_i, "t_ms": round(frame_i * 1000 / fps, 1),
                "dets": [[*map(float, b), float(s), int(c)] for b, s, c in zip(xyxy, sc, cl)]}) + "\n")
        n += len(buf); buf.clear()
    while True:
        ok, frame = cap.read()
        if not ok: break
        buf.append(frame)
        if len(buf) == batch: flush()
    if buf: flush()
    wall = time.perf_counter() - t0
    out.write(json.dumps({"stats": {"frames": n, "wall_s": round(wall, 2),
              "fps": round(n / wall, 1), "providers": providers}}) + "\n")
with open(dst, "rb") as fh:
    svc.get_blob_client(cont, os.environ["OUT_BLOB"]).upload_blob(fh, overwrite=True)
print(f"done frames={n} fps={n / wall:.1f} providers={providers}")
```

**4. Dockerfile (CUDA 12.8 + cuDNN runtime; about 2.86 GB compressed base + 277 MB ORT wheel)**

```dockerfile
FROM nvidia/cuda:12.8.1-cudnn-runtime-ubuntu24.04
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv \
 && rm -rf /var/lib/apt/lists/* && python3 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
# 1.26 = last CUDA-12 default build; >=1.27 defaults to CUDA 13 (needs driver >=580)
RUN pip install "onnxruntime-gpu==1.26.*" opencv-python-headless numpy azure-identity azure-storage-blob
WORKDIR /app
COPY artifacts/twincast-s.onnx /app/model.onnx
COPY detector.py job.py /app/
CMD ["python", "job.py"]
```

Size notes: `-devel` (5.87 GB) is only needed to compile. There is a slimmer variant to try: `nvidia/cuda:12.8.1-base` (0.10 GB) + `onnxruntime-gpu[cuda,cudnn]==1.26.*`, which pulls the NVIDIA pip wheels. Those wheels are not small either: cuDNN 766 MB + cuBLAS 581 MB on PyPI. Measure both. For the TensorRT EP, add `tensorrt-cu12` wheels matching the ORT TensorRT EP table (it lists TensorRT 10.9 for recent ORT).

**5. Create and run the job**

```bash
az containerapp env workload-profile add -g $RG -n $ENV \
  --workload-profile-name NC8as-T4 --workload-profile-type Consumption-GPU-NC8as-T4
az containerapp job create -g $RG -n cv-detect --environment $ENV --workload-profile-name NC8as-T4 \
  --trigger-type Manual --replica-timeout 1800 --replica-retry-limit 1 \
  --replica-completion-count 1 --parallelism 1 \
  --image $ACR.azurecr.io/cv-detect:1 --cpu 8 --memory 56Gi \
  --mi-system-assigned --registry-server $ACR.azurecr.io --registry-identity system \
  --env-vars STORAGE_ACCOUNT_URL=https://$SA.blob.core.windows.net VIDEO_BLOB=m4211/hero.mp4 \
             OUT_BLOB=m4211/detections.jsonl REQUIRE_GPU=1
# grant the job identity "Storage Blob Data Contributor" on $SA, then:
az containerapp job start -g $RG -n cv-detect
```

Links: rf-detr export docs (GitHub `docs/exports/`), the rf-detr CUDA export cookbook notebook, the ORT CUDA and TensorRT EP pages, and the ACA GPU image-generation tutorial (full CLI flow). All are listed under Sources.

## Sources

- rf-detr README (model table, licences, T4 latencies) — https://github.com/roboflow/rf-detr — accessed 20 Oct 2026
- rf-detr Export overview (measured performance by hardware, CPU 357–377 ms, latency caveats) — https://github.com/roboflow/rf-detr/blob/develop/docs/exports/index.md — accessed 20 Oct 2026
- rf-detr Export basics / advanced (parameters, extras, output files) — https://github.com/roboflow/rf-detr/blob/develop/docs/exports/basics.md and https://github.com/roboflow/rf-detr/blob/develop/docs/exports/advanced.md — accessed 20 Oct 2026
- rf-detr ONNX inference (outputs, decoding, INT8 CPU) — https://github.com/roboflow/rf-detr/blob/develop/docs/exports/onnx.md — accessed 20 Oct 2026
- rf-detr TensorRT export (FP16/INT8 T4 tables, engine sizes, portability, timing cache) — https://github.com/roboflow/rf-detr/blob/develop/docs/exports/tensorrt.md — accessed 20 Oct 2026
- rf-detr CUDA export cookbook (L4 ORT CUDA EP vs TensorRT table) — https://github.com/roboflow/rf-detr/blob/develop/docs/cookbooks/export-cuda.ipynb — accessed 20 Oct 2026
- rf-detr run/detection docs (`inference()` CUDA Graph) and CHANGELOG (`optimize_for_inference` removed in 1.11.0) — https://github.com/roboflow/rf-detr/blob/develop/docs/learn/run/detection.md ; https://github.com/roboflow/rf-detr/blob/develop/CHANGELOG.md — accessed 20 Oct 2026
- rfdetr on PyPI (1.11.2, extras) — https://pypi.org/project/rfdetr/ — accessed 20 Oct 2026
- ONNX Runtime CUDA Execution Provider — https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html — accessed 20 Oct 2026
- ONNX Runtime TensorRT Execution Provider — https://onnxruntime.ai/docs/execution-providers/TensorRT-ExecutionProvider.html — accessed 20 Oct 2026
- onnxruntime-gpu on PyPI (1.26.0 CUDA-12 deps vs 1.31.0 CUDA-13, wheel sizes) — https://pypi.org/project/onnxruntime-gpu/ — accessed 20 Oct 2026
- NVIDIA CUDA Toolkit release notes (driver minimums: 12.8 ≥570.26, 13.x ≥580) — https://docs.nvidia.com/cuda/cuda-toolkit-release-notes/index.html — accessed 20 Oct 2026
- NVIDIA trtexec README — https://github.com/NVIDIA/TensorRT/tree/main/samples/trtexec ; TensorRT 10.8 command-line programs — https://docs.nvidia.com/deeplearning/tensorrt/10.8.0/reference/command-line-programs.html — accessed 20 Oct 2026
- Using serverless GPUs in Azure Container Apps (regions, quota, software stack 570/12.x → 580/13.x, cold start) — https://learn.microsoft.com/en-us/azure/container-apps/gpu-serverless-overview — accessed 20 Oct 2026
- Reducing cold-start time on Azure Container Apps — https://learn.microsoft.com/en-us/azure/container-apps/cold-start — accessed 20 Oct 2026
- Tutorial: Generate images using serverless GPUs (NC8as-T4 profile, CLI, "up to five minutes") — https://learn.microsoft.com/en-us/azure/container-apps/gpu-image-generation — accessed 20 Oct 2026
- Workload profiles in Azure Container Apps — https://learn.microsoft.com/en-us/azure/container-apps/workload-profiles-overview — accessed 20 Oct 2026
- Jobs in Azure Container Apps — https://learn.microsoft.com/en-us/azure/container-apps/jobs ; az containerapp job CLI — https://learn.microsoft.com/en-us/cli/azure/containerapp/job — accessed 20 Oct 2026
- Request quota changes for Azure Container Apps — https://learn.microsoft.com/en-us/azure/container-apps/quota-requests — accessed 20 Oct 2026
- Azure Container Apps pricing (GPU "in addition to the active usage vCPU and RAM prices") — https://azure.microsoft.com/en-us/pricing/details/container-apps/ — accessed 20 Oct 2026
- Azure Retail Prices API (ACA GPU/vCPU/memory meters; ACR SKUs; NC4as_T4_v3 VM) — https://prices.azure.com/api/retail/prices — accessed 20 Oct 2026
- Artifact streaming (preview) in Azure Container Registry — https://learn.microsoft.com/en-us/azure/container-registry/container-registry-artifact-streaming — accessed 20 Oct 2026
- Azure ML endpoints for inference (online vs batch, scale to zero) — https://learn.microsoft.com/en-us/azure/machine-learning/concept-endpoints — accessed 20 Oct 2026
- Azure ML managed online endpoints VM SKU list (NC4as_T4_v3, 20% reservation) — https://learn.microsoft.com/en-us/azure/machine-learning/reference-managed-online-endpoints-vm-sku-list — accessed 20 Oct 2026
- nvidia/cuda image tags on Docker Hub (compressed sizes) — https://hub.docker.com/r/nvidia/cuda/tags — accessed 20 Oct 2026
- Roboflow Inference README and LICENSE (Apache-2.0 core, enterprise exceptions), Docker Hub images — https://github.com/roboflow/inference ; https://hub.docker.com/r/roboflow/roboflow-inference-server-gpu — accessed 20 Oct 2026
- Microsoft Q&A, NC8as-T4 replica sizing (secondary) — https://learn.microsoft.com/en-us/answers/questions/5823616/azure-container-app-consuption-profile-gpu-cost-ca — accessed 20 Oct 2026
