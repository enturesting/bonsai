from __future__ import annotations
from pydantic import BaseModel, Field

EMBED_DIM = 1024  # voyage-3, cosine

# ── Agent-under-test I/O ─────────────────────────────────────────────
class Source(BaseModel):
    id: str = ""                    # citation handle, e.g. "S3" (loader assigns "S{n}" if absent)
    title: str = ""
    url: str = ""
    text: str                       # the retrievable passage text (what a quote must match)

class AUTOutput(BaseModel):
    """One cited answer from the Gemini 3.5 AUT. The thing under test."""
    input: str                      # the question posed to the AUT
    claim: str                      # the single assertion being checked
    output: str                     # full answer text the AUT produced
    sources: list[Source] = Field(default_factory=list)

    @property
    def sources_text(self) -> str:  # deterministic checks grep against this
        return "\n".join(s.text for s in self.sources)

# ── Caught failure (the doc stored in Atlas `failures`) ──────────────
class Failure(BaseModel):
    id: str                         # slug, stable, unique  (Mongo _id == id)
    input: str                      # question that triggered the failure
    claim: str                      # the unsupported / wrong assertion
    expected: str                   # what a correct, supported answer looks like
    actual: str                     # what the AUT actually emitted (wrong)
    why: str                        # one-line diagnosis of the failure class
    embedding: list[float] = Field(default_factory=list, max_length=EMBED_DIM)
    # embedding: 1024-dim voyage-3 (input_type="document"); [] until embed() runs

# ── Reusable check (the rubric is list[Check]) ───────────────────────
class Check(BaseModel):
    id: str                         # slug, stable  (seed: "numeric-cites-source")
    property: str                   # the invariant, phrased over ROLES/TYPES not literals
    rationale: str                  # why this CLASS of failure matters
    positive_example: str           # a known-good output that MUST still pass
    negative_example: str           # the failure that motivated it (MUST fail)
    overfit_risk: str               # self-critique: how could this be too narrow?

# ── Verdict (output of any checker) ──────────────────────────────────
class Verdict(BaseModel):
    passed: bool
    confidence: float = Field(ge=0.0, le=1.0)  # Haiku self-report; det.=1.0; Opus=1.0
    reason: str
