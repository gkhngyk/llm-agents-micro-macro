# Background for the second study — written 2026-10-03

## 1. What the first study found

Paper: *LLMs Simulate the Description of a Culture, Not the Culture* —
preprint https://doi.org/10.5281/zenodo.23119302, data and code
https://doi.org/10.5281/zenodo.23118819, repo `../project-ultimatum`.

Three models (Claude Haiku 4.5, Gemma-4-31b-it, GPT-OSS-120b) played the
one-shot Ultimatum Game as responders with a WEIRD or a small-scale identity
card. For the same identities, game and offers, the result depended on how
the identity was described:

| Description | Offer-10 rejection, small-scale / WEIRD |
|---|---|
| Card with a numeric "fairness salience" score (Study 1) | 0.04 / 0.03 |
| Value-laden card: "reciprocity, sharing, kin network" (Study 2) | 0.61 / 0.06 |
| Minimal card: age and occupation only | 0.21 / 0.24 |
| Factual card: community size and market integration | 0.13 / 0.09 |

- Raising the fairness score from 0.3 to 0.6 on the same card raised
  low-offer rejection from 5 % to 52 % (three models, all conditions).
- No description reproduced Henrich's human pattern (WEIRD rejects more).
- A sentence saying the pot was earned jointly raised rejection sharply in
  Haiku and Gemma, not in GPT-OSS.
- Models differ a lot: Gemma rejects readily, GPT-OSS rarely, Haiku is the
  most sensitive to story framing.

## 2. Lessons about method

- The first design put a numeric disposition score on the cards; it produced
  the first result almost by itself. Found only after four follow-up tests.
- A batch clustering "blind coder" leaked the labels through sample order;
  replaced by per-text coding with two decision models (Jev 1.13, Span-01).
- A decision rule that anticipated only one direction mislabelled a strong
  reverse effect. Pre-specify both directions.
- Pilot runs caught three design confounds by reading reasoning texts, not
  by looking at rates.
- Profile seeds built with Python `hash()` were not reproducible.

## 3. What others have already published (see literature_scan.md)

- LLM groups in the repeated public goods game do not show the human decay
  of contributions; trajectories are flat or rising; punishment does not
  raise contributions (SILICA, arXiv:2608.28182; Teo, arXiv:2606.27845).
- Macro can look human while micro is wrong (Arruda et al., arXiv:2606.30454).
- Interaction can amplify, induce or reverse individual biases, depending on
  group size (Flint et al., PNAS 2026, arXiv:2510.22422).
- Not done by any of these: the same identity-description manipulation
  measured in isolation and after interaction; mixed-description groups;
  cultural identities; large closed models.

## 4. Candidate design (NOT fixed)

Question: when the identity description changes an isolated agent's
behaviour, does ten rounds of group interaction amplify, damp or preserve
that difference — and what happens in groups that mix descriptions?

- Game: repeated public goods game with and without punishment, after
  Herrmann, Thöni & Gächter (2008): groups of 4, 10 rounds, 20 tokens,
  marginal per-capita return 0.4, punishment at 1:3. Human data from 16
  participant pools, including individual-level punishment patterns
  ("antisocial punishment").
- Manipulation: three description styles (value-laden, minimal, factual).
- Arms: (i) isolated agent — conditional contribution schedule (strategy
  method); (ii) homogeneous groups; (iii) mixed-description groups.
- Analysis idea (from Flint et al.): use the isolated response function to
  predict what a group would do if interaction added nothing; compare with
  the observed group.

Known risk: if trajectories are flat, the answer is "preserved" — valid but
modest. The design should make that outcome informative too.

## 5. Open to-dos before any design is fixed

1. ~~Check that the Herrmann et al. (2008) data are available at the level
   needed (per pool, per round; ideally individual level) and under what terms.~~
   Done 2026-10-03, see section 6. Remaining: match city means to the 2008
   paper figures; get the SOM to learn what the `data` filter excludes.
2. Decide which cultural identities to simulate and how each of the three
   description styles is written for them.
3. Decide the isolated arm: full strategy method (contribution for each
   possible average of the others) or a shorter schedule.
4. Cost estimate per arm; pilot plan.
5. Write `prereg_<name>.md` before the first call.
6. Read SILICA's supplementary information and the final PNAS version of
   Flint et al. (not available when the scan was done).

## 6. Herrmann, Thöni & Gächter (2008) data — checked 2026-10-03

Source: Dryad doi:10.5061/dryad.87301 (Zenodo record 4969858), **CC0**.
Files in `data/herrmann2008/` (zip + README, SHA-256 in `SHA256SUMS`;
unpacked `raw/` is git-ignored). Structure check: `check_data.py`, output
`check_output.json` — all numbers below come from that file.

- **Individual level, every round.** 65 880 rows = one row per sender ×
  other group member × period × experiment. Per row: own contribution, the
  other's contribution, punishment points sent to that other (0–10), total
  punishment received, plus civic-norm and rule-of-law indices and
  demographics. Who-punished-whom is fully recoverable.
- 16 cities, groups of 4, 10 periods, contributions 0–20 — as in the paper.
- Participants: 1 120 in the P-experiment, matching "1120 participants"
  (Gächter, Herrmann & Thöni 2010, PMC2936171). Two sessions were split
  across two session ids each (Athens: periods 1–6 / 7–10, 28 subjects;
  Chengdu: N in one id, P in another, 20 subjects), so naive counts give
  1 148 / 1 168. 1 076 subjects played N (Zurich 44 played only P).
- **Order is not always N then P**, although the 2010 summary says "the
  first experiment always was" N: 156 subjects played P first (Minsk 36,
  Samara 72, St. Gallen 48) and 44 (Zurich) played P only. 900 subjects
  are in plain N→P sessions. Any human anchor must state which subset it
  uses; decide in the prereg.
- Pooled human decay is present in N (mean 10.82 in period 1 → 4.41 in
  period 10) and absent in P (11.02 → 13.26). City means range in P from
  5.70 (Athens) to 17.98 (Boston). Not yet checked against the 2008 paper's
  figures: the PDF could not be fetched (HTTP 403); do this before use.
- Antisocial punishment, defined as in the paper (points sent to someone
  who contributed the same or more than the punisher), as a share of all
  points sent: 0.18 (Nottingham) to 0.62 (Athens).
- **The published Stata code does not run on the published data**: it uses
  variables not in the file (`data` filter, `negdev`, `devclass`, `c`,
  `cityorder`, `dpun`). In particular we do not know what the `data` filter
  excludes. Definitions must be taken from the paper and SOM, and our own
  re-computation of the paper's figures is the check.

Consequence for the design: the anchor supports per-city, per-round and
per-individual comparison, including conditional contribution patterns
(own vs others' previous contributions) and antisocial punishment. Open
question B (cross-cultural, with description test) is feasible on data.
