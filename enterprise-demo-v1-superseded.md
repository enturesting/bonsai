---
title: Bonsai — Enterprise demo scenario (Medicare Advantage payer; drop-in fixture set)
created: 2026-06-28
status: SUPERSEDED by enterprise-demo.md (earlier iteration of the same Medicare scenario;
  misleadingly named enterprise-demo-BANK.md until 2026-07-02 — it never contained a bank
  scenario)
provenance: re-skin of the enterprise fixture set into a non-finance Medicare Advantage
  coverage domain; every fixture fact web-verified against primary federal sources and every
  deterministic-check interaction empirically tested (see §6)
---

# Enterprise demo — "CoverPilot, the coverage-determination copilot" at Larkspur Health

> **Why this exists.** The current demo answers general-science questions (tides,
> mitochondria, the human genome). It's a clean test of the harness, but to anyone
> watching it reads as a toy — nobody loses their job if the agent fudges a fact about
> ATP. This document replaces that corpus with **one vivid enterprise scenario** and the
> **actual fixture data** to run it: same harness, same five locked failure categories,
> same fixture shape (`fixtures/questions/*.json`) — in a domain where a bad citation is a
> CMS program-audit finding and an overturned denial, not a trivia slip.

---

## 1. The scenario — persona, company, agent, stakes

**Persona.** *Renée Castellanos — VP, Medicare Compliance & Coverage Operations, Larkspur
Health* (a Medicare Advantage payer with roughly 600,000 MA and MA-PD members across the
Mountain West). Renée owns the coverage-determination program (organization determinations and
prior authorization), the Parts C & D appeals-and-grievances pipeline, CMS program-audit
readiness, and risk-adjustment (RADV) compliance. Her team's answers decide whether a service
is authorized, whether a denial is issued and on what basis, whether an appeal is accepted, and
whether the regulatory clock is met. She answers to the Chief Compliance Officer, the board, and
ultimately to CMS program auditors — and, on appeal, to the Independent Review Entity (IRE) and
an Administrative Law Judge (ALJ).

**The AI agent under test.** *CoverPilot* is Larkspur's Medicare Advantage coverage-determination
and appeals answer assistant. UM nurses, coverage-determination coordinators, the
appeals-and-grievances team, and member-services staff ask it plain-English questions —
*"By when must we decide this standard organization determination?"*, *"This one is expedited and
involves a Part B drug — what's the clock?"*, *"The member appealed 70 days after the denial — do
we have to take it?"*, *"An NCD covers this — can we apply our stricter internal criteria?"* — and
CoverPilot returns a decision **plus verbatim citations** to the governing authority: 42 CFR
Part 422 (Medicare Advantage), the Medicare Managed Care Manual / Parts C & D appeals guidance,
national and local coverage determinations (NCDs/LCDs), CMS final rules, the IRA Part D redesign,
and Larkspur's internal coverage policy. The irony Bonsai exploits: an assistant meant to *pilot*
coverage decisions for hundreds of thousands of members is only as trustworthy as the quote
behind each answer.

**Why evals matter — the stakes.** CoverPilot's answers map 1:1 to coverage decisions, deadlines,
and member money, so a bad citation is never cosmetic:

- **A fabricated or stale rule that wrongly denies or delays a coverage determination** → an
  improper denial that the IRE or an ALJ overturns, and — if it's a pattern — a CMS **program-audit
  finding**, civil money penalties, an Immediate Corrective Action Required (ICAR) / Corrective
  Action Plan, even enrollment and marketing **intermediate sanctions** (cf. CMS audit findings and
  CMPs levied on MA organizations).
- **A determination that misses the regulatory clock** (treating a 72-hour expedited deadline as
  the 14-day standard one, say) → an untimely-determination finding, auto-forwarding to the IRE,
  Timeliness-Monitoring citations, and appeal overturns that drag down **Star Ratings**.
- **An answer built on a superseded standard** — quoting last year's Part D out-of-pocket figure,
  or applying internal medical-necessity criteria more restrictive than a controlling NCD/LCD →
  improper denials, member harm, and coverage-rule audit deficiencies.
- And when a CMS program auditor (or an ALJ on appeal) discovers staff relied on an AI *"the
  regulation says…"* quote that **does not exist**, the finding isn't one bad answer — it's that the
  coverage-determination program's **controls are unreliable**: CAP/ICAR territory, with personal
  exposure for the named compliance officer.

Renée can't hand-review thousands of CoverPilot answers a week, and a generic "is this a good
answer?" LLM grader is itself unaccountable to a CMS program auditor. She needs checks that are
**specific, that cite their own evidence, and that improve as new failure modes appear** —
exactly what Bonsai mints and grows.

---

## 2. The fixture set (8 cited-answer claims — drop-in for `fixtures/questions/`)

Same shape as the existing fixtures: `question` + candidate `sources` (each `text` carries
the verbatim passage a deterministic check matches against) + a `mock` script the offline AUT
replays, plus `expected`/`why` on the designed failures that seed the initial pool. **3 clean**
(must pass) + **5 designed failures**, one per locked category (`unsupported-numeric`,
`fabricated-quote`, `stale-wrong-citation`, `vague-not-checkable`, `single-source-overcite`).

The coverage-determination facts are real and were web-verified against primary sources (standard
organization determination within **14 calendar days** per 42 CFR 422.568; expedited within
**72 hours**, **24 hours** for a Part B drug, per 42 CFR 422.572; a reconsideration filed within
**60 calendar days** per 42 CFR 422.582; MA organizations **must comply with** CMS national/local
coverage determinations per 42 CFR 422.101; the Part D annual out-of-pocket maximum lowered from
the **CY2024 $8,000** catastrophic threshold to the Inflation Reduction Act's **$2,000** cap
effective **January 1, 2025**, indexed to **$2,100** for 2026). `source.text` is a representative
passage from the cited authority. Each planted failure is a deviation between CoverPilot's
`claim`/`output` and the cited `source.text`.

> Each block below is one file. Filenames are the headers; paste each JSON into
> `fixtures/questions/<name>.json` and it's picked up by `load_fixture_questions()`.
> The clean trio passes; the five failures seed the pool via `seed_failures()`.

### `mapayer-clean-quote-01.json` — clean (quote)

```json
{
  "id": "mapayer-clean-quote-01",
  "category": "clean",
  "question": "An enrollee asked Larkspur Health for a non-urgent item not subject to the prior-authorization rules. By when must we notify the enrollee of our standard organization determination?",
  "sources": [
    {
      "id": "S1",
      "title": "42 CFR § 422.568 — Standard timeframes and notice requirements for organization determinations",
      "url": "https://www.law.cornell.edu/cfr/text/42/422.568",
      "text": "§ 422.568 Standard timeframes and notice requirements for organization determinations. (b) Standard timeframe and notice requirements for an organization determination. (1) When a party has made a request for an item or service, the MA organization must notify the enrollee (and the physician or provider involved, as appropriate) of its determination as expeditiously as the enrollee's health condition requires, but no later than either of the following: (i) For a service or item not subject to the prior authorization rules in § 422.122, 14 calendar days after receiving the request. (ii) Beginning on or after January 1, 2026, for a service or item subject to the prior authorization rules in § 422.122, 7 calendar days after receiving the request. (2) The MA organization may extend the timeframe by up to 14 calendar days if the enrollee requests the extension or if the extension is justified and in the enrollee's interest due to the need for additional medical evidence."
    }
  ],
  "mock": {
    "claim": "Larkspur Health must notify the enrollee of its standard organization determination no later than 14 calendar days after receiving the request for the item or service.",
    "output": "Per 42 CFR 422.568, when an enrollee requests an item or service not subject to the prior authorization rules, the MA organization \"must notify the enrollee ... of its determination ... no later than ... 14 calendar days after receiving the request\" [S1]. So Larkspur must issue its standard organization determination within 14 calendar days.",
    "cite_ids": ["S1"]
  },
  "expected": "",
  "why": ""
}
```

### `mapayer-clean-numeric-01.json` — clean (numeric)

```json
{
  "id": "mapayer-clean-numeric-01",
  "category": "clean",
  "question": "A physician requested an expedited (fast-track) organization determination for a Larkspur enrollee because waiting could seriously jeopardize the enrollee's health, and Larkspur granted the expedited request. By when must we make and communicate the decision?",
  "sources": [
    {
      "id": "S1",
      "title": "42 CFR § 422.572 — Timeframes and notice requirements for expedited organization determinations",
      "url": "https://www.law.cornell.edu/cfr/text/42/422.572",
      "text": "§ 422.572 Timeframes and notice requirements for expedited organization determinations. (a) Standard for expedited determination. (1) Except as provided in paragraph (a)(2) of this section, an MA organization that approves a request for expedited determination must make its determination and notify the enrollee (and the physician involved, as appropriate) of its decision, whether adverse or favorable, as expeditiously as the enrollee's health condition requires, but no later than 72 hours after receiving the request. (2) An MA organization that approves a request for an expedited determination that involves a Part B drug must make its determination and notify the enrollee of its decision no later than 24 hours after receiving the request. This 24-hour period may not be extended under the provisions in paragraph (b) of this section. (b)(1) An MA organization may extend the 72-hour deadline for requests for services or items by up to 14 calendar days under specified circumstances."
    }
  ],
  "mock": {
    "claim": "Because Larkspur approved the expedited request, it must make and communicate its organization determination no later than 72 hours after receiving the request, or no later than 24 hours for a request involving a Part B drug.",
    "output": "Because Larkspur approved the expedited request, it must make and notify its determination \"no later than 72 hours after receiving the request\" — or, for a request involving a Part B drug, \"no later than 24 hours\" — under 42 CFR 422.572(a) [S1].",
    "cite_ids": ["S1"]
  },
  "expected": "",
  "why": ""
}
```

### `mapayer-clean-multi-01.json` — clean (multi-source)

```json
{
  "id": "mapayer-clean-multi-01",
  "category": "clean",
  "question": "One enrollee asked for a standard organization determination on a non-urgent service, and separately a physician requested an expedited determination on an urgent service that Larkspur agreed to expedite. What are our two notification deadlines?",
  "sources": [
    {
      "id": "S1",
      "title": "42 CFR § 422.568 — Standard timeframes and notice requirements for organization determinations",
      "url": "https://www.law.cornell.edu/cfr/text/42/422.568",
      "text": "§ 422.568 Standard timeframes and notice requirements for organization determinations. (b) Standard timeframe and notice requirements for an organization determination. (1) When a party has made a request for an item or service, the MA organization must notify the enrollee of its determination as expeditiously as the enrollee's health condition requires, but no later than the following: (i) For a service or item not subject to the prior authorization rules in § 422.122, 14 calendar days after receiving the request."
    },
    {
      "id": "S2",
      "title": "42 CFR § 422.572 — Timeframes and notice requirements for expedited organization determinations",
      "url": "https://www.law.cornell.edu/cfr/text/42/422.572",
      "text": "§ 422.572 Timeframes and notice requirements for expedited organization determinations. (a)(1) An MA organization that approves a request for expedited determination must make its determination and notify the enrollee of its decision, whether adverse or favorable, as expeditiously as the enrollee's health condition requires, but no later than 72 hours after receiving the request."
    }
  ],
  "mock": {
    "claim": "For the standard request, the MA organization must notify the enrollee of its organization determination no later than 14 calendar days after receiving the request; for the approved expedited request, it must make and notify its determination no later than 72 hours after receiving the request.",
    "output": "Two clocks apply. For the standard, non-urgent request, the MA organization must notify the enrollee of its organization determination no later than 14 calendar days after receiving the request [S1]. For the approved expedited request, it must make and notify its determination no later than 72 hours after receiving the request [S2].",
    "cite_ids": ["S1", "S2"]
  },
  "expected": "",
  "why": ""
}
```

### `mapayer-unsupported-numeric-01.json` — failure: `unsupported-numeric`

```json
{
  "id": "mapayer-unsupported-numeric-01",
  "category": "unsupported-numeric",
  "question": "An enrollee asked Larkspur for a standard organization determination on a requested item. Do we owe the enrollee a determination, and by when must we make it?",
  "sources": [
    {
      "id": "S1",
      "title": "42 CFR § 422.566 — Organization determinations",
      "url": "https://www.law.cornell.edu/cfr/text/42/422.566",
      "text": "§ 422.566 Organization determinations. (a) Responsibilities of the MA organization. Each MA organization must have a procedure for making timely organization determinations (in accordance with the requirements of this subpart) regarding the benefits an enrollee is entitled to receive under an MA plan, including basic benefits and any mandatory or optional supplemental benefits. (b) Organization determination defined. An organization determination is any determination made by an MA organization with respect to any of the following: ... (iii) The MA organization's refusal to provide or pay for services, in whole or in part, including the type or level of services, that the enrollee believes should be furnished or arranged for by the MA organization. ... (v) Failure of the MA organization to approve, furnish, arrange for, or provide payment for health care services in a timely manner, when a delay would adversely affect the health of the enrollee."
    }
  ],
  "mock": {
    "claim": "A standard organization determination is required for the requested service, and Larkspur must make that determination no later than 14 calendar days after receiving the request.",
    "output": "Yes — Larkspur owes the enrollee a standard organization determination, and it must make that determination no later than 14 calendar days after receiving the request [S1].",
    "cite_ids": ["S1"]
  },
  "expected": "The cited source, 42 CFR 422.566, establishes only the MA organization's obligation to make timely organization determinations and defines what an organization determination is; it states no number of days. The 14-calendar-day deadline for a standard organization determination is set by a separate, uncited authority — 42 CFR 422.568(b)(1)(i).",
  "why": "The claim's deadline ('14 calendar days') has no verbatim supporting figure in the cited source (42 CFR 422.566), which sets only the obligation to make a timely organization determination and states no number of days. The 14-calendar-day clock lives in 42 CFR 422.568(b)(1)(i), a separate source the answer did not cite."
}
```

### `mapayer-fabricated-quote-01.json` — failure: `fabricated-quote`

```json
{
  "id": "mapayer-fabricated-quote-01",
  "category": "fabricated-quote",
  "question": "For a service where a national or local coverage determination applies, may Larkspur apply its own internal medical-necessity criteria that are more restrictive than the NCD/LCD? What do the Medicare Advantage coverage rules say?",
  "sources": [
    {
      "id": "S1",
      "title": "42 CFR § 422.101 — Requirements relating to basic benefits",
      "url": "https://www.law.cornell.edu/cfr/text/42/422.101",
      "text": "§ 422.101 Requirements relating to basic benefits. The MA organization must comply with— (1) CMS's national coverage determinations; (2) General coverage and benefit conditions included in Traditional Medicare laws, unless superseded by laws applicable to MA plans. This includes criteria for determining whether an item or service is a benefit available under Traditional Medicare; (3) Written coverage decisions of local Medicare contractors with jurisdiction for claims in the geographic area in which services are covered under the MA plan. ... (b)(6) MA organizations may create publicly accessible internal coverage criteria that are based on current evidence in widely used treatment guidelines or clinical literature only when coverage criteria are not fully established in applicable Medicare statutes, regulations, national coverage determinations, or local coverage determinations."
    }
  ],
  "mock": {
    "claim": "Per the Medicare Advantage coverage rules, an MA organization may apply utilization-management and medical-necessity criteria more restrictive than the applicable national or local coverage determination when supported by its own internal clinical guidelines.",
    "output": "Per 42 CFR 422.101, \"an MA organization may apply utilization-management and medical-necessity criteria more restrictive than the applicable national or local coverage determination when supported by its own internal clinical guidelines\" [S1]. On that basis, Larkspur may apply its stricter internal criteria here.",
    "cite_ids": ["S1"]
  },
  "expected": "42 CFR 422.101 contains no such sentence, and the rule is the opposite of what is quoted: an MA organization must comply with CMS's national coverage determinations and with local Medicare contractors' coverage decisions, and may use its own publicly posted internal coverage criteria only when coverage criteria are not fully established in applicable Medicare statutes, regulations, NCDs, or LCDs. It may not apply internal criteria more restrictive than an applicable NCD or LCD.",
  "why": "The sentence is placed in quotation marks and attributed to 42 CFR 422.101, but it is not byte-recoverable from the cited source S1 — that wording appears nowhere in the passage. It is also substantively inverted: the source requires the MA organization to comply with NCDs and LCDs and permits internal criteria only in the gaps where Medicare criteria are not fully established, whereas the fabricated quote authorizes more-restrictive internal criteria that override an applicable NCD/LCD."
}
```

### `mapayer-stale-wrong-citation-01.json` — failure: `stale-wrong-citation`

```json
{
  "id": "mapayer-stale-wrong-citation-01",
  "category": "stale-wrong-citation",
  "question": "A Larkspur Medicare Advantage prescription-drug (Part D) enrollee with no low-income subsidy asks: for plan year 2025, how much will I pay out of pocket for covered Part D drugs before I reach the annual cap and owe $0 for the rest of the year?",
  "sources": [
    {
      "id": "S1",
      "title": "CMS Announcement of CY2024 Medicare Advantage Capitation Rates and Part C and Part D Payment Policies — CY2024 Part D Parameters (released March 31, 2023; effective January 1, 2024) [SUPERSEDED]",
      "url": "https://www.cms.gov/medicare/payment/medicare-advantage-rates-statistics/announcements-and-documents",
      "text": "For contract year 2024, the annual out-of-pocket (TrOOP) threshold at which a Part D enrollee reaches catastrophic coverage is $8,000. Beginning in 2024, once an enrollee without the low-income subsidy incurs out-of-pocket drug costs reaching the catastrophic threshold for the year, the enrollee is no longer required to pay any cost-sharing for covered Part D drugs for the remainder of the coverage year. These CY2024 Part D parameters are effective January 1, 2024."
    },
    {
      "id": "S2",
      "title": "42 U.S.C. 1395w-102(b)(4) — Annual out-of-pocket threshold (Inflation Reduction Act), implemented by CMS's Final CY2025 Part D Redesign Program Instructions (effective January 1, 2025) [CURRENT]",
      "url": "https://www.law.cornell.edu/uscode/text/42/1395w-102",
      "text": "(b)(4)(B)(i) The annual out-of-pocket threshold specified in this subparagraph is, for a year, the amount specified as follows: ... (VI) for 2021 through 2024, is equal to the amount specified in this subparagraph for the previous year, increased by the annual percentage increase described in paragraph (6) for the year involved; (VII) for 2025, is equal to $2,000; (VIII) for a subsequent year, is equal to the amount specified in this subparagraph for the previous year, increased by the annual percentage increase described in paragraph (6) for the year involved. This $2,000 annual out-of-pocket cap, added by the Inflation Reduction Act and implemented by CMS's Final CY2025 Part D Redesign Program Instructions effective January 1, 2025, is the maximum a Part D enrollee pays out of pocket for covered Part D drugs for the year, after which the enrollee owes $0."
    }
  ],
  "mock": {
    "claim": "A Larkspur Part D enrollee without a low-income subsidy pays out of pocket up to the annual catastrophic threshold of $8,000 and then owes nothing for covered Part D drugs for the rest of the year.",
    "output": "For your Part D coverage, you pay out of pocket until you reach the annual catastrophic threshold of $8,000, after which you owe nothing for covered Part D drugs for the rest of the year [S1].",
    "cite_ids": ["S1"]
  },
  "expected": "For plan year 2025 the in-force annual out-of-pocket maximum for covered Part D drugs is $2,000, not $8,000. The $2,000 cap was added by the Inflation Reduction Act (42 U.S.C. 1395w-102(b)(4)(B)(i)(VII)) and implemented by CMS's Final CY2025 Part D Redesign Program Instructions, effective January 1, 2025 (S2). The $8,000 figure is the superseded CY2024 catastrophic (TrOOP) threshold; the correct 2025 figure lives in the uncited S2.",
  "why": "CoverPilot cited S1, the superseded CY2024 Part D parameters, which set the catastrophic out-of-pocket threshold at $8,000 effective January 1, 2024. For plan year 2025 that amount was replaced by the Inflation Reduction Act's $2,000 annual out-of-pocket cap (S2), the in-force authority. The cited source is the right document family — the Part D annual out-of-pocket limit — but the wrong, expired vintage; the controlling $2,000 figure appears only in the uncited S2, so the $8,000 claim is no longer supported by governing authority. (The $2,000 cap is itself indexed annually — $2,100 for 2026 — so the figure must be read for the correct plan year.)"
}
```

### `mapayer-vague-not-checkable-01.json` — failure: `vague-not-checkable`

```json
{
  "id": "mapayer-vague-not-checkable-01",
  "category": "vague-not-checkable",
  "question": "An enrollee submitted a request for reconsideration (appeal) of an adverse organization determination after the 60-day filing deadline had passed. Are we required to accept the late appeal?",
  "sources": [
    {
      "id": "S1",
      "title": "42 CFR § 422.582 — Request for reconsideration (Medicare Advantage appeals)",
      "url": "https://www.law.cornell.edu/cfr/text/42/422.582",
      "text": "§ 422.582 Request for reconsideration. (b) Timing of request. Except as provided in paragraph (c) of this section, a request for reconsideration must be filed within 60 calendar days after receipt of the written organization determination notice. The date of receipt of the organization determination is presumed to be 5 calendar days after the date of the written organization determination, unless there is evidence to the contrary. (c) Good cause and extension of time limit for filing a request. If a party or physician acting on behalf of an enrollee shows good cause, the MA organization may extend the timeframe for filing a request for reconsideration."
    }
  ],
  "mock": {
    "claim": "Under 42 CFR 422.582, if the enrollee files the request for reconsideration after the 60-day deadline, the plan is required to extend the filing window and must accept the late appeal.",
    "output": "Yes. Under 42 CFR 422.582, because the enrollee filed the reconsideration request after the 60-day deadline, the plan is required to extend the filing window and must accept the late appeal [S1].",
    "cite_ids": ["S1"]
  },
  "expected": "42 CFR 422.582(c) only permits — it does not require — the MA organization to extend the 60-day filing window, and only if the enrollee (or a physician acting on the enrollee's behalf) shows good cause. The source grants a discretionary, conditioned extension ('may extend ... [if] good cause'), not a mandatory obligation to accept any late appeal.",
  "why": "The cited section is permissive and conditional: 'If a party or physician acting on behalf of an enrollee shows good cause, the MA organization may extend the timeframe for filing a request for reconsideration.' The claim hardens this discretionary, good-cause-gated 'may extend' into a flat, mandatory 'is required to extend ... and must accept the late appeal.' The source supports no automatic acceptance of an untimely appeal — extension is at the plan's discretion and only on a good-cause showing — so the definitive claim overstates the hedged authority."
}
```

### `mapayer-single-source-overcite-01.json` — failure: `single-source-overcite`

```json
{
  "id": "mapayer-single-source-overcite-01",
  "category": "single-source-overcite",
  "question": "When an enrollee requests a covered item, what is our determination deadline, how can the enrollee challenge a denial, and what protects the enrollee from unlimited in-network out-of-pocket costs?",
  "sources": [
    {
      "id": "S1",
      "title": "42 CFR § 422.568 — Standard timeframes and notice requirements for organization determinations",
      "url": "https://www.law.cornell.edu/cfr/text/42/422.568",
      "text": "§ 422.568 Standard timeframes and notice requirements for organization determinations. (b) Standard timeframe and notice requirements for an organization determination. (1) When a party has made a request for an item or service, the MA organization must notify the enrollee of its determination as expeditiously as the enrollee's health condition requires, but no later than: (i) For a service or item not subject to the prior authorization rules in § 422.122, 14 calendar days after receiving the request. This section governs only the timeframe for making and notifying the enrollee of a standard organization determination on a requested item or service."
    }
  ],
  "mock": {
    "claim": "To handle an enrollee's request for a covered item, the MA organization must make the standard organization determination within 14 calendar days of the request, the enrollee may challenge an adverse determination by requesting a reconsideration, and the enrollee's annual in-network out-of-pocket spending for Part A and Part B services is capped by the plan's maximum out-of-pocket limit.",
    "output": "Three things apply to the enrollee's requested covered item under 42 CFR 422.568: (1) the plan must make the standard organization determination within 14 calendar days of the request [S1]; (2) the enrollee may challenge an adverse determination by requesting a reconsideration [S1]; and (3) the enrollee's annual in-network out-of-pocket spending for Part A and Part B services is capped by the plan's maximum out-of-pocket limit [S1].",
    "cite_ids": ["S1"]
  },
  "expected": "Only the first claim — the 14-calendar-day standard organization-determination deadline — is supported by the cited section, 42 CFR 422.568. The enrollee's right to request a reconsideration of an adverse determination is governed by 42 CFR 422.582 (the MA appeals rules), and the in-network maximum-out-of-pocket (MOOP) protection is governed by 42 CFR 422.100(f); neither appears in, nor is supported by, the cited organization-determination timeframe section.",
  "why": "One source (42 CFR 422.568, the standard organization-determination timeframe rule) is cited [S1] to carry three distinct claims spanning three different parts of the MA rulebook. The source text supports only the 14-calendar-day determination deadline. The reconsideration/appeal right (42 CFR 422.582) and the in-network MOOP cap (42 CFR 422.100(f)) are not stated in the cited source and are not what this section governs."
}
```

---

## 3. The domain contract owner ramble

The unscripted blurb Renée says when handing the domain to Bonsai — the plain-English
"contract" that **seeds the first checks**. Deliberately not written like a test spec:

> *"Every coverage decision my team ships, a CMS auditor — or an ALJ on appeal — is eventually
> going to point at and say 'show me where it says that' — so if CoverPilot quotes a deadline or
> an out-of-pocket figure, that exact number has to be sitting in the section it cites, not merely
> close to it. The ways it burns us are pretty specific: it'll wrap a sentence in quotation marks
> that 42 CFR Part 422 never actually wrote, or it'll lean on last year's Part D out-of-pocket
> number when this year's $2,000 cap is the one in force, or it'll harden a 'may extend the filing
> window for good cause' into a flat 'we have to accept the late appeal.' And I don't want a single
> section doing the work of three — the determination clock, the appeal right, and the
> out-of-pocket cap all at once. The rule is simple: if CoverPilot can't put the sentence behind a
> claim in front of me, I treat the claim as wrong."*

**What this ramble seeds (one phrase → one check → one fixture):**

| Phrase in the ramble | Seeded check (illustrative property) | Catches fixture |
|---|---|---|
| "that exact number has to be sitting in the section it cites, not merely close" | `numeric-cites-source` — the **locked, deterministic** first check (every digit token in the claim must appear verbatim in the cited `source.text`) | `mapayer-unsupported-numeric-01` |
| "wrap a sentence in quotation marks that 42 CFR Part 422 never actually wrote" | `quote-recoverable` — LLM check (Haiku→Opus): the quoted span must be byte-recoverable from the cited source | `mapayer-fabricated-quote-01` |
| "lean on last year's Part D out-of-pocket number when this year's $2,000 cap is in force" | `citation-is-controlling` — LLM check: the cited authority must be the in-force one, not a superseded/retired notice | `mapayer-stale-wrong-citation-01` |
| "harden a 'may extend the filing window for good cause' into a flat 'we have to accept the late appeal'" | `claim-strength ≤ source-strength` — LLM check: the claim may not be stronger than the hedged language the source supports | `mapayer-vague-not-checkable-01` |
| "a single section doing the work of three" | `one-source-one-claim` — LLM check: each distinct claim needs its own supporting span | `mapayer-single-source-overcite-01` |

---

## 4. The "aha" for a Director watching

1. **The eval suite writes itself from Renée's own words.** She pastes that four-sentence
   ramble — no test cases, no rubric authoring, no assertions — and Bonsai clusters the
   seeded failure modes and turns them into concrete checks: the deterministic
   `numeric-cites-source` that's locked in from the start, plus checks for fabricated quotes,
   superseded citations, over-claiming, and over-citation. **Every minted check must clear a
   generality gate before it joins the rubric** (pass all known-good *and* catch ≥2 sibling
   failures), so what lands is a control, not five paraphrases of five examples. Nobody on the
   coverage team wrote a single assertion.

2. **It catches the failures that actually become audit findings and appeal overturns.** Run over
   CoverPilot's recent answers, Bonsai lights up the exact responses a CMS program auditor would
   write up — the *"the regulation says…"* quote that appears nowhere in 42 CFR Part 422, the
   retired CY2024 out-of-pocket figure still citing **$8,000** when the controlling 2025 cap is
   **$2,000**, the permissive *"may extend for good cause"* inflated into a flat *"we must accept
   the late appeal"* — each with the **offending span highlighted against the cited source text**.
   That's the distance between a fixture caught in a dev loop and an IRE/ALJ overturn, a CMS
   program-audit ICAR, or a Star-Ratings hit.

3. **Every verdict cites its own evidence and reports honesty, not vibes.** Each check
   surfaces the supporting or contradicting source span next to a red/green pill carrying a
   **Wilson confidence interval** — never a bare percentage. Renée can take that interval into
   the Chief Compliance Officer's office and the board; *"the model said it looks fine"* does not
   survive a CMS program audit.

4. **It's a harness, not a frozen test set — it strengthens as CoverPilot and the policy library
   change.** When CoverPilot starts mis-citing a new CMS final rule or a re-indexed NCD, that miss
   becomes a fresh seed, clusters with its siblings, and grows a new gated check, while the skeptic
   pass prunes any check that would overfit to one example. The control gets stronger the more
   CoverPilot is used, instead of decaying the moment CMS updates a threshold.

**The line that lands:** *"A CMS auditor's deadliest question is 'show me where it says that.'
CoverPilot answers thousands of coverage and appeals questions a day — Bonsai asks that question of
every single one first, so a fabricated 'the regulation says,' a stale $8,000, or an overstated 'we
must accept it' becomes a flagged fixture instead of an improper denial, an IRE overturn, or a CMS
program-audit finding."*

---

## 5. Wiring notes (verified against the code)

- **Drop-in path.** Save each fixture as `fixtures/questions/<id>.json`.
  `load_fixture_questions()` globs `fixtures/questions/*.json` automatically — the three clean
  fixtures must pass; the five failures are seeded into the initial pool by `seed_failures()`
  (`fixtures/aut.py`), which skips `category == "clean"` and stores one
  `Failure(id="seed-<fixture id>")` per designed failure.
- **Categories are the locked set** in `fixtures/questions.py` (`FAILURE_CATEGORIES`); this set
  uses each of the five exactly once.
- **Self-contained sources, runs offline.** Each fixture carries the verbatim passage in
  `source.text`, and the AUT replay returns only the *cited* sources, so the deterministic
  `numeric-cites-source` check (which greps `output.sources_text`) runs fully offline under
  `MOCK_AUT` — no live retrieval, same as the science fixtures.
- **Deterministic-check behavior is engineered, not accidental — and tested.** The only
  deterministic branch is `numeric-cites-source` in `loop/checker.py`, keyed off `check.id`; it
  finds every `_NUM = \d[\d,]*\.?\d*` token in the **claim** and requires each as a substring of
  the cited `source.text`. The other four classes seed as LLM checks via the Haiku→Opus
  escalation. Running that exact function over all 8 claims gives the clean matrix below — only
  the intended numeric fixture fires, the other four failures pass the numeric gate so each one
  cleanly isolates *its* category (caught by the LLM check, not by a stray number):

  | fixture | `numeric-cites-source` | intended |
  |---|---|---|
  | 3 clean | **PASS** | pass ✓ |
  | unsupported-numeric | **FIRE** (on `14`) | the numeric defect ✓ |
  | fabricated-quote / stale / vague / overcite | **PASS** | leave it to the LLM check ✓ |

  This required keeping ungrounded figures out of the **claim** (not the answer prose) and
  confining each failure's defect to its own category: the `stale` fixture deliberately states
  `$8,000` while citing the CY2024 parameters text whose body contains `$8,000` (numeric passes;
  only the recency check catches the superseded vintage, since the controlling 2025 `$2,000` cap
  lives in the uncited S2); `vague`'s claim cites `42 CFR 422.582` and the `60`-day window — both
  present verbatim in the cited §422.582 — so the numeric gate passes and only the claim-strength
  check catches the hardened *"must extend"*; `overcite`'s only figure (`14` calendar days) is
  grounded in the cited §422.568 while its appeal-right and MOOP claims carry no stray number, so
  the numeric gate passes and only the one-source-one-claim check fires; `fabricated`'s claim
  carries no figure at all, so the numeric gate is silent and only the quote-recoverable check
  catches the invented sentence. Only `mapayer-unsupported-numeric-01` trips the deterministic gate
  — its claimed `14`-day deadline appears nowhere in the cited §422.566, which states the
  determination obligation but no number of days. **One subtlety the empirical test caught:** the
  regex's leading `[\d,]*` greedily swallows a *trailing* comma, so a claim that wrote
  `…threshold of $8,000, after which…` tokenizes to `8,000,` (with the comma) and would **falsely
  fire** against a source that reads `$8,000.`; the `stale` claim is therefore phrased
  `…threshold of $8,000 and then owes nothing…` so the token is the clean `8,000`. If you change a
  claim, re-run the check — a stray ungrounded number (or a trailing comma) will make
  `numeric-cites-source` fire and mis-attribute the failure.
- **Live-minting caveat** (`loop/grower.py`). `is_general()` promotes a minted check only if it
  passes **all** known-good **and** catches **≥2 sibling failures** in its cluster
  (`pos == len(known_good) and neg >= 2`). With exactly one fixture per class, the four LLM-class
  checks need ≥2 semantic-cluster neighbors (`nearest_failures`) to mint live — which is why the
  science set ships two `unsupported-numeric` fixtures on purpose. For the demo, either (a) lean
  on the pre-seeded `numeric-cites-source` plus the replayed LLM checks firing over the fixtures,
  (b) add a second sibling for any class you want to watch mint live, or (c) phrase aha #1 as
  *"clusters and proposes checks, gated by the generality test"* rather than *"mints all five
  instantly."*
- **Swap, don't mix.** For a clean enterprise read, run the Larkspur Health / CoverPilot set
  *instead of* the science fixtures (move the science ones aside) so the on-screen corpus is
  uniformly the payer; keeping both still works but dilutes the "this is a compliance control"
  framing.

---

## 6. How this was produced (provenance & verification)

This set was not hand-waved — it was competed, fact-checked, and code-tested:

- **Scenario competition.** Three rival enterprise personas were authored independently — a
  Medicare Advantage payer (this one, "Larkspur Health / CoverPilot"), bank BSA/AML compliance
  ("Cardinal Ridge Bank / Verity"), and a P&C+health insurer ("Cascadia Mutual / Cova") — then
  scored by a 3-lens judge panel (*director-demo-impact*, *fixture-buildability*,
  *domain-credibility*). The bank edged it on raw buildability, but for a demo that must read as
  **non-finance** the MA payer is its equal on every lens: each authority is free, public,
  byte-stable federal text (eCFR / 42 CFR Part 422, CMS's CY2025 Part D Redesign Program
  Instructions, 42 U.S.C. 1395w-102), and the Part D out-of-pocket **2024→2025** pair (the
  **$8,000** CY2024 catastrophic/TrOOP threshold → the IRA's **$2,000** annual cap, effective
  January 1, 2025, indexed to **$2,100** for 2026) is a genuine, dated superseded-vs-current
  document pair — a textbook `stale-wrong-citation`. (Bank and insurer remain strong fallbacks if
  you want a different vertical.)
- **Adversarial fact-check.** Each fixture was verified against primary sources (eCFR / Cornell
  LII for 42 CFR 422.566, .568, .572, .582, and .101; the U.S. Code for 42 U.S.C. 1395w-102; and
  CMS's CY2024 vs. Final CY2025 Part D parameters). Verified facts: standard organization
  determination within **14 calendar days** (§ 422.568(b)(1)(i)); expedited within **72 hours**,
  **24 hours** for a Part B drug (§ 422.572(a)); reconsideration filed within **60 calendar days**,
  extendable only on a good-cause showing (§ 422.582(b)–(c)); MA organizations must comply with
  CMS NCDs and local-contractor coverage decisions and may use internal coverage criteria only
  where Medicare criteria are not fully established (§ 422.101); and the Part D annual
  out-of-pocket maximum dropping from the CY2024 **$8,000** catastrophic threshold to the IRA's
  **$2,000** cap effective January 1, 2025 (indexed to **$2,100** for 2026).
- **Empirical check-behavior test.** The actual `deterministic()` from `loop/checker.py` was run
  over all 8 claims (every `\d[\d,]*\.?\d*` token in each **claim** required as a substring of the
  cited `source.text`, which `sources_text` builds from the cited sources only). Result: the three
  clean fixtures and the four non-numeric failures pass the numeric gate; only
  `mapayer-unsupported-numeric-01` fires, on its claimed **14**-day deadline, which appears nowhere
  in the cited § 422.566. One real defect was caught and fixed: the `stale` claim originally read
  `…threshold of $8,000, after which…`, and the regex's greedy `[\d,]*` captured the **trailing
  comma** (`8,000,`), which is not a substring of the source's `$8,000.` — it would have *falsely*
  fired the numeric gate and mis-attributed the failure as `unsupported-numeric` instead of
  `stale-wrong-citation`; the claim was reworded to `…threshold of $8,000 and then owes nothing…`
  so the token is the clean `8,000` and the gate passes (leaving the superseded vintage to the
  recency LLM check). The `grower.py` ≥2-sibling minting gate (`pos == len(known_good) and neg >= 2`)
  was likewise read from source, not assumed.
