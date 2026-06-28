#!/usr/bin/env python
"""Live proof: Bonsai's agent-under-test runs on real Gemini 3.5 (Vertex AI / ADC).

This is the *real* (non-mock) path — it makes one live Gemini call and prints the
cited answer. Use it on camera or in Q&A to show the harness isn't canned: the AUT
is genuinely Gemini 3.5, drawing GCP credit through ADC.

    ./.venv/bin/python scripts/gemini_live.py

Needs: gcloud ADC (`gcloud auth application-default login`) for the Vertex default,
or set GEMINI_BACKEND=aistudio with GEMINI_API_KEY. Nothing here touches the
deterministic web demo (WEB_MOCK_STREAM=1) — it's a separate, additive smoke call.
"""
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from config import get_settings  # noqa: E402
from fixtures.gemini_client import gemini_answer  # noqa: E402
from store.models import Source  # noqa: E402

cfg = get_settings()
print("─" * 64)
print("Bonsai agent-under-test — LIVE Gemini call (not the mock)")
print(f"  backend={cfg.gemini_backend}  model={cfg.gemini_model}")
print(f"  project={cfg.google_cloud_project}  location={cfg.google_cloud_location}")
print("─" * 64)

sources = [
    Source(id="S1", title="Access Review Policy",
           text="User access reviews are conducted on a periodic basis aligned with role risk."),
    Source(id="S2", title="Encryption Standard",
           text="Customer data is encrypted at rest with AES-256 and in transit with TLS 1.2 or higher."),
]
question = "How is customer data encrypted, at rest and in transit?"
print(f"Q: {question}\n")

t0 = time.time()
out = gemini_answer(question, sources)
latency = round(time.time() - t0, 2)

print(f"Gemini 3.5 answered in {latency}s:")
print(f"  answer: {out.output}")
print(f"  load-bearing claim: {out.claim}")
print(f"  cited sources: {[s.id for s in out.sources]}")
print("─" * 64)
print("^ real Gemini 3.5 via Vertex AI (GCP credit). The harness then checks this")
print("  claim against its cited source — that check loop is what Bonsai grows.")
