# 03 — Microsoft Foundry / Azure OpenAI for the Explain and Personalise stages

_Accessed/compiled: 20 Oct 2026 · Priority area: Explain + Personalise (LLM layer, translation, speech)_

## TL;DR

- **Call models with the plain `openai` Python SDK against the Azure OpenAI v1 endpoint** (`https://<resource>.openai.azure.com/openai/v1/`). No `api-version`, and no `AzureOpenAI()` client. Auth is either an API key or Entra ID via `DefaultAzureCredential` + `get_bearer_token_provider(..., "https://ai.azure.com/.default")`. The product is now called **Microsoft Foundry**, and model docs live under "Foundry Models".
- **Use structured outputs (`responses.parse(..., text_format=Insight)`) for the cue JSON.** The schema rules are strict: every field required, `additionalProperties: false`, at most 100 properties and 5 nesting levels, and no `minLength`/`maxItems`/`pattern`. One gotcha: structured outputs are **not supported in Foundry Agent Service** (prompt agents). That is a reason to call the model directly.
- **Live path: a small model (`gpt-5.4-nano` / `gpt-5.4-mini`, or the newer `gpt-6-luna`), one call per *moment* not per event, a low `max_output_tokens`, `reasoning_effort` low or `none`, and a stable prompt prefix of at least 1,024 tokens for prompt caching.** Use Global Standard deployments. Provisioned is only worth it for low latency variance at scale.
- **Grounding: compute every number in Python, pass the numbers in as context, require `evidence_event_ids`, then check the IDs and the numbers in code after generation.** Never trust a number the model typed.
- **Microsoft Agent Framework** (`pip install agent-framework`) replaces both Semantic Kernel and AutoGen. Its own docs say *"If you can write a function to handle the task, do that instead of using an AI agent."* About 40-50 rival teams ship agent crews. A deterministic pipeline that verifies its own numbers is how we stand out.

## Findings

### 1. Calling a model from Python today

| Topic | What the docs say |
|---|---|
| Endpoint | v1 API (GA since Aug 2025): `OpenAI(base_url="https://YOUR-RESOURCE-NAME.openai.azure.com/openai/v1/")`. `*.services.ai.azure.com/openai/v1/` also works. The docs recommend the **Responses API** for Azure OpenAI models. The v1 chat-completions syntax also works for other Foundry models (DeepSeek, Grok, MAI). |
| Auth | Key: `api_key=os.getenv("AZURE_OPENAI_API_KEY")`. Entra ID: pass a token provider as `api_key`, and the `OpenAI()` client refreshes the token automatically. Your identity needs the **Cognitive Services OpenAI User** role. |
| Foundry project endpoint | `https://<service>.services.ai.azure.com/api/projects/<project>`. Agent Framework's `FoundryChatClient` and Agent Service use this endpoint. |
| No-deploy option | "Instant access (preview)" lets you call supported models by name without creating a deployment. |

**Deployment types (what matters for latency).** Start with **Global Standard**: it gets new models first, has the lowest price and the broadest regions, and data may be processed in any region. **Data Zone Standard** keeps processing inside the EU, US or APAC zone and has lower default quota. Standard types are best-effort, and *"customers with high consistent volume might experience greater latency variability."* **Provisioned** (PTU) gives *"lower and more consistent latency"* but is reserved capacity, which is overkill for a hackathon. **Global Batch** costs 50% less and targets a 24-hour turnaround, which suits offline recap generation only. Global Standard also offers per-request **Priority processing** (faster, at about 2x the list price per the retail price meters) and **Flex processing** (cheaper, delay-tolerant).

**Latency formula:** `TTLT = TTFT + (TBT × tokens generated)`. Output tokens dominate. *"Each prompt token adds little time compared to each incremental token generated."* The docs' tips are:
- set `max_tokens` as low as possible;
- use stop sequences;
- set `n=1`;
- stream when a human watches the text appear;
- use separate deployments per workload, so short live calls don't queue behind long recaps and cache hit rates stay higher;
- remember that content filtering adds latency.

### 2. Models you can verify on Learn (Oct 2026)

From "Foundry Models sold by Azure" (updated 8 Oct 2026). Availability varies by region, so check the region-availability page before you pick a region.

| Family | Models (current, not retired) | Notes for us |
|---|---|---|
| GPT-6.1 / GPT-6 | `gpt-6.1-sol`, `gpt-6-astra`, `gpt-6-luna`, `gpt-6-sol` | Structured outputs and streaming supported. Some quota tiers must request quota. Short/long-context pricing. |
| GPT-5.6 | `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna` | Default `reasoning_effort` is medium. Chat Completions plus tools fails unless effort is `none`, so use the Responses API. |
| GPT-5.5 / 5.4 | `gpt-5.5`, `gpt-5.4`, `gpt-5.4-pro`, `gpt-5.4-mini`, `gpt-5.4-nano` | mini/nano: 400K context, 128K max output, structured outputs supported. |
| GPT-5 / 5.1 / 5.2 | `gpt-5`, `gpt-5-mini`, `gpt-5-nano`, `gpt-5.1`, `gpt-5.2`, codex variants | `gpt-5.1` defaults to `reasoning_effort=none`. |
| GPT-4.1 | `gpt-4.1`, `gpt-4.1-mini`, `gpt-4.1-nano` | Non-reasoning. Structured outputs on chat completions. |
| Others sold by Azure | MAI-Thinking-1 (preview), DeepSeek-V4/V3.2, Grok 4.x, Llama-4-Maverick, Mistral-Large-3, Kimi-K2.x, `model-router` | Mostly English/Chinese language lists. |
| Partner/community | **Phi-4-mini-instruct**, Phi-4, Phi-4-reasoning, Phi-4-mini-reasoning, Phi-4-multimodal-instruct; Claude models | Phi-4-mini: no tool calling, 4,096 output tokens, and **Bulgarian is not in its language list**. |

Reasoning effort accepts `none`, `minimal`, `low`, `medium`, `high`, `xhigh` and `max`, depending on the model. The docs recommend `none` for *"latency-critical work … such as voice, fast information retrieval, and classification."* `minimal` only works on the original GPT-5 models. The `verbosity` parameter (`low`/`medium`/`high`) controls how concise the output is.

### 3. Structured outputs for the cue JSON

- Chat Completions uses `response_format`. Responses uses `text.format` (in the SDK: `responses.parse(text_format=PydanticModel)`, then read `output_parsed`). Use **OpenAI Python 2.x** for `responses.parse`.
- Rules:
  - all fields are required (model an optional field as `type: ["string","null"]`);
  - `additionalProperties: false` on every object;
  - at most **100 properties and 5 nesting levels**;
  - output keys follow the schema order;
  - `anyOf` is allowed but not at the root;
  - `$defs` and recursion work.
- Unsupported keywords: `minLength`, `maxLength`, `pattern`, `format`, `minimum`, `maximum`, `minItems`, `maxItems`, `uniqueItems`. **Enforce these in code.**
- Structured outputs don't work with parallel function calls (set `parallel_tool_calls=false`), with Assistants, or with **Foundry Agents Service**.
- The supported-models list on the structured-outputs page stops at GPT-5.1. The model tables list "Structured outputs" for 5.4-mini/nano, 5.5, 5.6 and 6.x.

### 4. Prompt caching and other speed tips

- Caching is automatic when a prompt has at least **1,024 tokens** and **the first 1,024 tokens are identical**. One character of difference means a miss. Hits show up as `usage.prompt_tokens_details.cached_tokens`.
- The structured-output **schema is added as a prefix to the system message**, so keep the schema and system prompt byte-stable. Put the per-moment stats last.
- In-memory caches are usually cleared after *"5 to 10 minutes of inactivity"* and always within one hour. Extended 24h retention (`prompt_cache_retention: "24h"`) exists for listed models such as `gpt-5.4` and `gpt-4.1`; `gpt-5.4-mini` is not on that list.
- On GPT-5.6 and later, **cache writes are billed**. Use `prompt_cache_key`, and note that above roughly 15 requests per minute per prefix+key, some requests miss the cache.
- Streaming: `client.responses.create(..., stream=True)` and read `response.output_text.delta` events. A mid-stream error still returns HTTP 200 and arrives as an `error` event, so handle it.

### 5. Quotas and rate limits (gotchas)

- **TPM is checked against an *estimate* made when the request arrives: prompt plus `max_tokens`**, not the billed tokens. A large `max_tokens` therefore burns quota even when replies are short.
- **RPM is enforced over 1-second or 10-second windows.** A burst of requests at a goal can return 429 even when you are under the per-minute limit. Example from the docs: a 600-RPM deployment allows about 10 requests per second.
- Quota tiers (Free plus Tiers 1-6) upgrade automatically with usage. Tier 1 Global Standard defaults include:

  | Model | RPM | TPM |
  |---|---|---|
  | `gpt-5.4-mini` | 1,000 | 1,000,000 |
  | `gpt-5.4-nano` | 5,000 | 5,000,000 |
  | `gpt-6-luna` | 1,000 | 1,000,000 |
  | `gpt-4.1-mini` | 5,000 | 5,000,000 |

  The lowest tier listed ("Tier 0") gives `gpt-5-mini` 500 RPM / 500,000 TPM.
- Quota is moving to a **subscription-level pool** (from 7 May 2026, rolling out model by model).
- The SDK retries **2 times by default**. Raise `max_retries`, and read `retry-after-ms` and the `x-ratelimit-remaining-*` headers. Failed requests still count toward the limit.

### 6. Translator, Speech, Content Safety

- **Translator**: Bulgarian (`bg`) is supported for text translation, Custom Translator, auto-detect, dictionary, transliteration and **LLM translation**. The new GA text API version **`2026-06-06`** lets you pick an LLM and supports adaptive custom translation (5-10,000 segment pairs). v3 is still GA.
- **Speech TTS**: Bulgarian neural voices `bg-BG-KalinaNeural` (F) and `bg-BG-BorislavNeural` (M). British voices include `en-GB-SoniaNeural`, `en-GB-RyanNeural` and `en-GB-LibbyNeural`. HD voices use names like `en-US-Ava:DragonHDLatestNeural`. Whether multilingual voices can speak Bulgarian is not documented on that page (unverified).
  - The SDK emits **`synthesis_word_boundary`** events (audio_offset, text_offset, duration) and **viseme** events. Events arrive faster than playback, so you must sync them to playback yourself. This is how captions and overlays can line up with voiced commentary.
- **Content Safety**:
  - text/image harm analysis;
  - **Prompt Shields**;
  - groundedness detection (preview, **English only**, 50 RPS on S0);
  - protected-material detection.

  Foundry's built-in content filters run on every call already. A separate Content Safety call is only needed for user-typed input such as a fan question (idea D Chalk Talk, 22 Half-Time Talk).

### 7. Rough cost (USD, list price, Global, East US 2)

These figures come from Microsoft's official Azure Retail Prices API. The Azure OpenAI pricing page lists these models, but its price cells did not render in our fetch. The page also says GPT-6 prices are *"in processing for publishing"*, so treat the GPT-6 row as provisional.

| Model (Global Standard) | Input / 1M | Cached input / 1M | Output / 1M |
|---|---|---|---|
| `gpt-5.4-nano` | $0.20 | $0.02 | $1.25 |
| `gpt-5.4-mini` | $0.75 | $0.075 | $4.50 |
| `gpt-5-mini` | $0.25 | $0.025 | $2.00 |
| `gpt-5-nano` | $0.05 | $0.005 | $0.40 |
| `gpt-5.6-luna` (short ctx) | $0.20 | $0.02 (+$0.25 cache write) | $1.20 |
| `gpt-6-luna` (short ctx) | $0.10 | $0.01 (+$0.125 cache write) | $0.50 |
| `gpt-5.4` | $2.50 | — | $15.00 |

Other services:
- Speech neural TTS (S1): $15 per 1M characters; Neural HD TTS: $22 per 1M characters.
- Translator S1: $10 per 1M characters.
- Content Safety text: $0.375 per 1,000 records.

Our arithmetic, not a quote: one moment call on `gpt-5.4-mini` with about 1,000 cached plus 500 fresh input tokens and 250 output tokens costs about $0.0016. Sixty explained moments per match is about $0.10.

## So what for us

**Stages: Explain, Personalise, and partly Render (TTS timing).**

1. **Architecture:** a deterministic Python Interpret stage (stats, thresholds, "why this matters" features) feeds **one model call per moment**. That call returns one `Insight` with both `casual_text` and `analyst_text`. We validate it, then turn it into a cue. No agent crew. This is the cheapest, fastest setup and the easiest to defend to judges against the 40-50 "studio crew + fact-checker" entries. Our "fact-checker" is code, and it fills the cue's `truth_check` field.
2. **Model choice:**
   - Live path: deploy `gpt-5.4-nano` on Global Standard, with `gpt-5.4-mini` as the quality fallback. Try `gpt-6-luna` if the subscription has quota for it, since it is the cheapest per token.
   - Offline recaps (13 Recap Dial, 11 Player Diary, 14 Comic Recap): Flex or Batch.
   - Skip Phi for anything multilingual.
3. **Ideas this helps most:**
   - **F Graphics Desk** (AI-proposed cues are structured outputs; take/hold is human);
   - **A TwinCast** (explained overlays; the grading report can cite evidence IDs);
   - **C One Number** (single-metric text variants);
   - **12 Jargon Buster** and **10 Story Time** (audience variants in the same schema);
   - **21 Called It** and **18 Signed Recap** (verified numbers plus evidence IDs give the audit trail).
   - **B Speed Trap** name tags should be pure templates with **no LLM** in the hot path. The LLM only adds the "so what" line.
4. **Multi-language:** generate in English, then translate with Translator `2026-06-06` (Bulgarian is fully supported). That is cheaper and more predictable than asking the LLM per language, and numbers survive translation untouched. Optional TTS uses `bg-BG-KalinaNeural` and `en-GB-RyanNeural`, with word-boundary events driving caption timing.
5. **Guardrails to build day one:**
   - keep `max_output_tokens` around 300;
   - give the client `max_retries=5`;
   - queue cue requests so a goal burst doesn't trip the 1-second RPM window;
   - keep the system prompt plus schema stable and over 1,024 tokens so it caches.

## Reuse: code & links

**Client (Entra ID, works locally with `az login`, and in Azure Container Apps with managed identity):**

```python
from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://ai.azure.com/.default")
client = OpenAI(
    base_url="https://YOUR-RESOURCE-NAME.openai.azure.com/openai/v1/",
    api_key=token_provider,      # or os.getenv("AZURE_OPENAI_API_KEY")
    max_retries=5,               # SDK default is 2; honours retry-after
)
```

**Insight with structured outputs, plus post-generation verification:**

```python
import json, re
from pydantic import BaseModel

class Insight(BaseModel):
    headline: str                 # enforce length in code (maxLength unsupported)
    why_it_matters: str
    evidence_event_ids: list[str]
    casual_text: str
    analyst_text: str

SYSTEM = open("prompts/explainer_system.md").read()  # stable, >=1,024 tokens, never edited mid-match

def explain_moment(moment: dict, stats: dict, events: list[dict]) -> Insight:
    ctx = {"moment": moment, "stats": stats,
           "events": [{"id": e["id"], "t": e["clock"], "type": e["type"], "player": e["player"]} for e in events]}
    resp = client.responses.parse(
        model="gpt-5.4-nano",                     # your deployment name
        instructions=SYSTEM,
        input="Explain this moment. Use ONLY numbers present in STATS. "
              "Cite the event ids you relied on.\n" + json.dumps(ctx),
        text_format=Insight,
        max_output_tokens=300,
        reasoning={"effort": "low"},              # check per-model allowed values
    )
    ins = resp.output_parsed
    verify(ins, stats, {e["id"] for e in events})
    return ins

NUM = re.compile(r"-?\d+(?:\.\d+)?")

def allowed_numbers(stats: dict) -> set[str]:
    out = set()
    for v in json.dumps(stats).replace('"', " ").split():
        for n in NUM.findall(v):
            f = float(n)
            out |= {n, f"{f:.0f}", f"{f:.1f}"}
    return out

def verify(ins: Insight, stats: dict, event_ids: set[str]) -> None:
    bad_ids = set(ins.evidence_event_ids) - event_ids
    text = " ".join([ins.headline, ins.why_it_matters, ins.casual_text, ins.analyst_text])
    bad_nums = {n for n in NUM.findall(text) if n not in allowed_numbers(stats)}
    if bad_ids or bad_nums or not ins.evidence_event_ids:
        raise ValueError(f"truth_check failed ids={bad_ids} nums={bad_nums}")  # retry once, then template fallback
```

**Streaming (only for free-text commentary or voice, not for cue JSON):**

```python
stream = client.responses.create(model="gpt-5.4-mini", input=prompt, stream=True)
for event in stream:
    if event.type == "response.output_text.delta":
        print(event.delta, end="")
    elif event.type == "error":
        break   # mid-stream errors arrive as events with HTTP 200
```

**Microsoft Agent Framework minimal agent (only if we need tool use, for example Chalk Talk Q&A):**

```python
# pip install agent-framework
import asyncio
from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential

agent = Agent(
    client=FoundryChatClient(
        project_endpoint="https://your-foundry-service.services.ai.azure.com/api/projects/your-foundry-project",
        model="gpt-5.4-mini",
        credential=AzureCliCredential(),
    ),
    name="HelloAgent",
    instructions="You are a friendly assistant. Keep your answers brief.",
)
print(asyncio.run(agent.run("Why did the press break down at 63'?")))
```

**Bulgarian TTS with word-boundary timing for captions:**

```python
import os, azure.cognitiveservices.speech as speechsdk
cfg = speechsdk.SpeechConfig(subscription=os.environ["SPEECH_KEY"], region=os.environ["SPEECH_REGION"])
cfg.speech_synthesis_voice_name = "bg-BG-KalinaNeural"
synth = speechsdk.SpeechSynthesizer(speech_config=cfg, audio_config=None)
synth.synthesis_word_boundary.connect(
    lambda e: print((e.audio_offset + 5000) / 10000, "ms", e.text))  # offset -> ms, as in docs
result = synth.speak_text_async("Натискът на гостите се срина след 63-тата минута.").get()
```

Repos and samples:
- Agent Framework: https://github.com/microsoft/agent-framework
- v1 API OpenAPI spec: https://github.com/Azure/azure-rest-api-specs/blob/main/specification/ai/data-plane/OpenAI.v1/azure-v1-v1-generated.json
- Retail Prices API, for scripted cost checks: `https://prices.azure.com/api/retail/prices?$filter=serviceName eq 'Foundry Models' and armRegionName eq 'eastus2'`

## Sources

- Azure OpenAI in Microsoft Foundry Models v1 API — https://learn.microsoft.com/en-us/azure/foundry/openai/api-version-lifecycle — accessed 20 Oct 2026
- How to use structured outputs — https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/structured-outputs — accessed 20 Oct 2026
- Understanding deployment types in Microsoft Foundry Models — https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/deployment-types — accessed 20 Oct 2026
- Foundry Models sold by Azure — https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure — accessed 20 Oct 2026
- Foundry Models from partners and community (Phi) — https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/models-from-partners — accessed 20 Oct 2026
- Prompt caching — https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/prompt-caching — accessed 20 Oct 2026
- Performance & latency — https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/latency — accessed 20 Oct 2026
- Reasoning models (reasoning_effort, verbosity) — https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/reasoning — accessed 20 Oct 2026
- Responses API (streaming) — https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/responses — accessed 20 Oct 2026
- Quotas and limits — https://learn.microsoft.com/en-us/azure/foundry/openai/quotas-limits — accessed 20 Oct 2026
- Manage quota / rate limits — https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/quota — accessed 20 Oct 2026
- Microsoft Agent Framework overview — https://learn.microsoft.com/en-us/agent-framework/overview/ — accessed 20 Oct 2026
- What is Foundry Agent Service? — https://learn.microsoft.com/en-us/azure/foundry/agents/overview — accessed 20 Oct 2026
- Translator overview — https://learn.microsoft.com/en-us/azure/ai-services/translator/overview — accessed 20 Oct 2026
- Translator language support — https://learn.microsoft.com/en-us/azure/ai-services/translator/language-support — accessed 20 Oct 2026
- Speech language support (TTS voices) — https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=tts — accessed 20 Oct 2026
- How to synthesize speech (Python, word boundary/viseme) — https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-speech-synthesis?pivots=programming-language-python — accessed 20 Oct 2026
- What is Azure AI Content Safety? — https://learn.microsoft.com/en-us/azure/ai-services/content-safety/overview — accessed 20 Oct 2026
- Azure OpenAI pricing page (prices did not render in fetch; GPT-6 note) — https://azure.microsoft.com/en-us/pricing/details/azure-openai/ — accessed 20 Oct 2026
- Azure Retail Prices API (source of the USD figures above, East US 2) — https://prices.azure.com/api/retail/prices — accessed 20 Oct 2026
