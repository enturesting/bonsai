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


_vertex = None


def _vertex_client(cfg):
    """Lazy singleton google-genai Vertex client — one transport, reused across the
    9-fixture AUT run (a fresh client per call can close the shared httpx transport)."""
    global _vertex
    if _vertex is None:
        from google import genai

        _vertex = genai.Client(
            vertexai=True,
            project=cfg.google_cloud_project,
            location=cfg.google_cloud_location,
        )
    return _vertex


def _answer_text(cfg, question: str, candidate_sources: "list[Source]") -> str:
    """Drive the configured Gemini backend; return the raw JSON response text.

    GEMINI_BACKEND=vertex (default): google-genai over Vertex AI using ADC — draws the
    GCP project's credit, no per-key prepay, and serves the Gemini 3.5 model from the
    `global` location. GEMINI_BACKEND=aistudio: the legacy API-key path (needs GEMINI_API_KEY).
    """
    prompt = _build_prompt(question, candidate_sources)

    if cfg.gemini_backend == "vertex":
        from google.genai import types

        resp = _vertex_client(cfg).models.generate_content(
            model=cfg.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM,
                response_mime_type="application/json",
                max_output_tokens=1024,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        return resp.text

    # aistudio (API-key) fallback
    if not cfg.gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is empty; set it, use GEMINI_BACKEND=vertex, or run MOCK_AUT=1."
        )
    import google.generativeai as genai  # imported lazily so the package loads keyless

    genai.configure(api_key=cfg.gemini_api_key)
    model = genai.GenerativeModel(
        cfg.gemini_model,
        system_instruction=_SYSTEM,
        generation_config={"response_mime_type": "application/json"},
    )
    return model.generate_content(prompt).text


def gemini_answer(question: str, candidate_sources: "list[Source]") -> AUTOutput:
    """Call Gemini 3.5 over one question + candidate sources -> cited AUTOutput.

    PRIVATE. The returned AUTOutput.sources are the *cited* candidate sources (full
    text preserved) so deterministic checks can match verbatim quotes against them.
    Backend is selected by GEMINI_BACKEND (vertex default); callers still gate the
    whole call behind the MOCK_AUT flag for the offline path.
    """
    cfg = get_settings()
    data = json.loads(_answer_text(cfg, question, candidate_sources))

    by_id = {s.id: s for s in candidate_sources}
    cited = [by_id[cid] for cid in data.get("citations", []) if cid in by_id]
    return AUTOutput(
        input=question,
        claim=data["claim"],
        output=data["answer"],
        sources=[Source(**s.model_dump()) for s in cited],
    )
