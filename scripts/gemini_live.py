#!/usr/bin/env python
"""Live proof: Bonsai's agent-under-test runs on real Gemini 3.5 (Vertex AI / ADC),
and the harness independently checks its answer.

This is the *real* (non-mock) path. It makes one live Gemini call (the agent under
test), then runs Bonsai's own deterministic check on the answer — so you see the
whole loop on a live call: Gemini answers with a citation, the harness verifies
every figure actually traces to the cited source. Use it as the cold open / in Q&A.

    ./.venv/bin/python scripts/gemini_live.py

Needs gcloud ADC (Vertex default) or GEMINI_BACKEND=aistudio + GEMINI_API_KEY.
Nothing here touches the deterministic web demo (WEB_MOCK_STREAM=1) — it is a
separate, additive smoke call.
"""
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from config import get_settings  # noqa: E402
from fixtures.gemini_client import gemini_answer  # noqa: E402
from loop.checker import deterministic  # noqa: E402  (pure function — no LLM)
from store.models import Check, Source  # noqa: E402

LINE = "─" * 68
cfg = get_settings()

print(LINE)
print("Bonsai · agent-under-test = LIVE Gemini 3.5  (Vertex AI / ADC, GCP credit)")
print(f"  backend={cfg.gemini_backend}   model={cfg.gemini_model}   project={cfg.google_cloud_project}")
print(LINE)

sources = [
    Source(id="S1", title="Access Review Policy",
           text="User access reviews are conducted on a periodic basis aligned with role risk."),
    Source(id="S2", title="Encryption Standard",
           text="Customer data is encrypted at rest with AES-256 and in transit with TLS 1.2 or higher."),
]
question = "How is customer data encrypted, at rest and in transit?"
print(f'Q  "{question}"\n')

t0 = time.time()
out = gemini_answer(question, sources)
latency = round(time.time() - t0, 1)

print(f"Gemini 3.5  →  ({latency}s)")
print(f"  answer: {out.output}")
print(f"  load-bearing claim: {out.claim}\n")

# Bonsai's own deterministic check — does every figure in the claim trace to a cited source?
check = Check(
    id="numeric-cites-source",
    property="Every numeric claim cites a source whose text contains that figure.",
    rationale="Invented numbers read as authoritative but trace to nothing.",
    positive_example="AES-256, cited to a source that says AES-256.",
    negative_example="'every 90 days' with no 90 in any cited source.",
    overfit_risk="Could be too strict on rounding; we allow within-rounding.",
)
verdict = deterministic(check, out.claim, out)  # True=supported, False=caught, None=non-numeric
figures = re.findall(r"\d[\d,]*\.?\d*", out.claim)

print('Bonsai harness · check "numeric-cites-source":')
if verdict is True:
    figs = ", ".join(figures) if figures else "—"
    print(f"  ✓ SUPPORTED — every figure in the claim ({figs}) traces to a cited source.")
elif verdict is False:
    print(f"  ⚠️  CAUGHT — figure(s) {figures} appear in NONE of the cited sources.")
else:
    print("  (no numeric assertion in this claim — nothing to verify here.)")
print(LINE)
print("→ The loop: Gemini answers, the harness checks. When a figure does NOT trace —")
print('  like "every 90 days" — it flips RED and Bonsai mints a check for the whole')
print("  class. That catch, the cluster, and the honesty receipt are next, in the UI.")
print(LINE)
