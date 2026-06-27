"""
fixtures/gemini_client.py — the ONLY Gemini (non-Anthropic) call site in Bonsai.

`gemini_answer` is PRIVATE to this module: it is imported by fixtures.aut for the
real (non-mock) path and is never re-exported from the `fixtures` package. It drives
the bleeding-edge Gemini 3.5 agent-under-test (targets the $5k Gemini prize): given a
question and candidate sources, it produces a cited answer and we extract the single
load-bearing claim.

No Anthropic / Voyage / Mongo imports here — this seam is Gemini-only.
"""
from __future__ import annotations

import json

from config import get_settings
from store.models import AUTOutput, Source

# Instruct the AUT to answer ONLY from the candidate sources, cite by id, and surface
# the single load-bearing assertion so the harness has a clean unit to evaluate.
_SYSTEM = (
    "You are a research assistant that answers strictly from the provided candidate "
    "sources. Cite the sources you used by their id (e.g. S1). Do not use outside "
    "knowledge. Respond ONLY with a JSON object of the form:\n"
    '{"answer": "<full answer with [S#] citation markers>", '
    '"claim": "<the single load-bearing assertion of your answer>", '
    '"citations": ["S1", ...]}'
)


def _format_sources(candidate_sources: "list[Source]") -> str:
    blocks = []
    for s in candidate_sources:
        head = f"[{s.id}]" + (f" {s.title}" if s.title else "")
        blocks.append(f"{head}\n{s.text}")
    return "\n\n".join(blocks)


def _build_prompt(question: str, candidate_sources: "list[Source]") -> str:
    return (
        f"{_SYSTEM}\n\n"
        f"Candidate sources:\n{_format_sources(candidate_sources)}\n\n"
        f"Question: {question}"
    )


def gemini_answer(question: str, candidate_sources: "list[Source]") -> AUTOutput:
    """Call Gemini 3.5 over one question + candidate sources -> cited AUTOutput.

    PRIVATE. The returned AUTOutput.sources are the *cited* candidate sources (full
    text preserved) so deterministic checks can match verbatim quotes against them.
    Raises if GEMINI_API_KEY is unset — callers gate this behind the MOCK_AUT flag.
    """
    cfg = get_settings()
    if not cfg.gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is empty; set it or run with MOCK_AUT=1 for the offline AUT."
        )

    import google.generativeai as genai  # imported lazily so the package loads keyless

    genai.configure(api_key=cfg.gemini_api_key)
    model = genai.GenerativeModel(
        cfg.gemini_model,
        system_instruction=_SYSTEM,
        generation_config={"response_mime_type": "application/json"},
    )
    resp = model.generate_content(_build_prompt(question, candidate_sources))
    data = json.loads(resp.text)

    by_id = {s.id: s for s in candidate_sources}
    cited = [by_id[cid] for cid in data.get("citations", []) if cid in by_id]
    return AUTOutput(
        input=question,
        claim=data["claim"],
        output=data["answer"],
        sources=[Source(**s.model_dump()) for s in cited],
    )
