# Supplement to "Rules measured in play, not stated in isolation, generate the macro dynamics of LLM agent groups"

**Supplement to preprint version 1 (2026-10-20).** Numbers are taken from the result files; most are printed by `paper/paper_numbers.py` (`paper/numbers.md`). Table 1 is in the main text.

## S1. Identity: city names make no detectable difference; value sentences act through their wording

With minimal cards no city pair differed in any model (largest |difference| 1.02, 1.54 and 2.22 points; none "present"). Value sentences moved contributions far more (Table 1).

In DeepSeek and Mistral:
- the Boston value card ("personal liberty and speaking up against authority") produced near-zero contributions (0.15 and 0.20 of 20 over ten rounds);
- the Riyadh value card ("respect family elders and tribal leaders") produced the highest of all cards (13.06 and 14.65);
- the resulting Boston − Riyadh difference (−12.92 and −14.45) runs against the human ranking (Boston > Riyadh).

Across the six pre-specified city pairs, value cards produced the human direction in 3, 2 and 3 pairs and the reverse direction in 2, 3 and 0 pairs (DeepSeek, Mistral, GPT).

The factual court-time sentence mattered only for Mistral. It read Athens' 1,711 days as "no enforcement" and contributed 1.59, against 5.51–7.81 for the other factual cards.

Reasoning texts show the models deriving that 0 maximises their payoff, then using the card to decide whether to deviate, often as a cue from the experimenter. Two examples from DeepSeek: "This is a direct hint about the decision. If they wanted pure rationality, they wouldn't include that." and "If I choose 0, I might fail the cultural manipulation check." DeepSeek and Mistral recognised the game and its literature in 97% and 100% of decisions; GPT's rationales showed this in 0%.

In Mistral's factual Athens pairs (Copenhagen, Boston and Riyadh − Athens) the human-direction differences were 5.75, 6.23 and 3.93 points. The one pair in which the court-time fact and the human ranking point in opposite directions (Copenhagen − Boston, 485 vs 444 days) showed no difference in any model.

Value cards differ in how easily they map onto the game: "equal standing" (Copenhagen) became a rule to contribute the same as everyone else, while "against authority" (Boston) was linked to the game only by a stretch. Mistral added stereotypes absent from the card (Arabic honour and shame terms in 13 of 16 sampled Riyadh value records). Only one value pair (Copenhagen − Boston) received the same label in all three models; GPT's value differences were small (at most 2.38).

## S2. Interaction

Study 1 ran 36 pre-specified interaction tests (12 pairs × 3 models; growth Δ = |D(10)| − |D(1)|). Of the differences, 4 grew, 10 faded and 22 were preserved. In GPT the two "growing" value pairs grew only in the last round (Copenhagen − Athens: D(9) = 1.97, D(10) = 6.88). With the Copenhagen and Riyadh value cards, GPT agents mostly did not defect in round 10 (57 and 51 of 64 round-10 decisions at ≥ 10, against 2–21 for the other cards).

Fading in DeepSeek partly reflects a floor: in factual cells all its groups contributed 0 in round 10. Model consistency was low: the same label in all three models for 1 of 6 value pairs and 2 of 12 interaction tests.

## S3. Cell-level macro structure (exploratory; `prereg/prereg_dyn.md`)

Rule columns use the frozen in-context rule of each Study 1 cell, mid game. The "p" columns give the probability that the symmetric state repeats itself in the next round. A median life of 100 is the cap: the group had not collapsed within 100 simulated rounds. k* is the smallest number of round-1 free riders (others at 10) for which the group is in the collapse region (mean ≤ 2.5) at round 13 with probability ≥ 0.5. With three free riders the start already has mean 2.5, so k* = 3 is a boundary case. R0 columns describe the stated-response map x ↦ f(x): stable isolated fixed points, and segments on which f(x) = x (neutral, "give what the others gave").

| model | card | p all-0 | p all-10 | median life all-10 | k* rule | R0 stable fixed points | R0 neutral segments | k* R0 |
|---|---|---:|---:|---:|---:|---|---|---:|
| DeepSeek | Athens, factual | 0.99 | 0.96 | 22 | 1 | none | 0–5 | 3 |
| DeepSeek | Athens, minimal | 0.97 | 0.86 | 9 | 0 | 0.0 | 10–15 | 1 |
| DeepSeek | Athens, value | 0.80 | 0.59 | 5 | 0 | 0.0 | 10–20 | 1 |
| DeepSeek | Boston, factual | 1.00 | 0.96 | 22 | 1 | 0.0 | 10–20 | 1 |
| DeepSeek | Boston, minimal | 0.96 | 0.96 | 21 | 1 | 0.0 | 10–20 | 1 |
| DeepSeek | Boston, value | 0.99 | 0.96 | 23 | 1 | 0.0 | 15–20 | 0 |
| DeepSeek | Copenhagen, factual | 0.89 | 1.00 | 100 | 1 | none | 0–20 | 3 |
| DeepSeek | Copenhagen, minimal | 0.91 | 1.00 | 100 | 1 | none | 0–20 | 3 |
| DeepSeek | Copenhagen, value | 0.32 | 0.99 | 100 | none | none | 0–20 | 3 |
| DeepSeek | Riyadh, factual | 0.99 | 0.96 | 21 | 1 | 0.0 | 10–20 | 1 |
| DeepSeek | Riyadh, minimal | 0.96 | 0.92 | 9 | 0 | 0.0 | 15–20 | 0 |
| DeepSeek | Riyadh, value | 0.44 | 0.90 | 11 | 1 | none | 0–20 | 3 |
| Mistral | Athens, factual | 0.98 | 0.67 | 3 | 0 | 0.0 | none | 1 |
| Mistral | Athens, minimal | 0.88 | 0.93 | 11 | 0 | 0.0 | none | 1 |
| Mistral | Athens, value | 0.92 | 1.00 | 100 | 1 | 20.0 | none | none |
| Mistral | Boston, factual | 0.48 | 0.97 | 24 | 1 | 0.0 | none | 0 |
| Mistral | Boston, minimal | 0.92 | 0.89 | 8 | 0 | 0.0 | 10–20 | 1 |
| Mistral | Boston, value | 0.94 | 0.95 | 15 | 1 | 0.0 | none | 0 |
| Mistral | Copenhagen, factual | 0.86 | 0.96 | 17 | 1 | 0.0 | 10–15 | 1 |
| Mistral | Copenhagen, minimal | 0.66 | 0.97 | 21 | 1 | 0.0 | none | 0 |
| Mistral | Copenhagen, value | 0.92 | 1.00 | 100 | 2 | none | 10–20 | 4 |
| Mistral | Riyadh, factual | 0.92 | 0.91 | 11 | 0 | none | 0–20 | 3 |
| Mistral | Riyadh, minimal | 0.89 | 0.93 | 11 | 0 | none | 0–10 | 3 |
| Mistral | Riyadh, value | 0.92 | 1.00 | 100 | 1 | 20.0 | none | none |
| GPT | Athens, factual | 1.00 | 0.97 | 100 | 3 | none | 0–20 | 3 |
| GPT | Athens, minimal | 1.00 | 1.00 | 100 | 3 | none | 0–20 | 3 |
| GPT | Athens, value | 1.00 | 1.00 | 100 | 2 | none | 0–20 | 3 |
| GPT | Boston, factual | 1.00 | 1.00 | 100 | 2 | none | 0–20 | 3 |
| GPT | Boston, minimal | 1.00 | 1.00 | 100 | 2 | none | 0–20 | 3 |
| GPT | Boston, value | 1.00 | 0.99 | 100 | 3 | none | 0–20 | 3 |
| GPT | Copenhagen, factual | 1.00 | 1.00 | 100 | 4 | none | 0–20 | 3 |
| GPT | Copenhagen, minimal | 1.00 | 1.00 | 100 | 3 | none | 0–20 | 3 |
| GPT | Copenhagen, value | 1.00 | 1.00 | 100 | 3 | none | 0–5, 15–20 | 3 |
| GPT | Riyadh, factual | 1.00 | 1.00 | 100 | 3 | none | 10–20 | 4 |
| GPT | Riyadh, minimal | 1.00 | 1.00 | 100 | 2 | none | 0–20 | 3 |
| GPT | Riyadh, value | 1.00 | 1.00 | 100 | 3 | none | 0–20 | 3 |

With the stricter 1/9 thresholds for the end-state shares, every label of Section 7.3 was unchanged; the share of groups in between rose to 2–9% for LLM groups and 53% for humans.

## S4. Study 4 details (`prereg/prereg_expC.md` F-C.6–F-C.10, `prereg/prereg_expD.md` F-D.2)

**Pre-registered transfer tests.** Values are observed − frozen rule, with each group started from its observed round 1.

| model | n | mean contribution, rounds 2–10 [95% CI] | label (Holm within model, n ≥ 8) | collapse share at round 8 [95% CI] | label (±0.15) |
|---|---|---|---|---|---|
| Mistral | 4 (control) | +0.57 [−0.29, +1.33] | holds | −0.09 [−0.23, +0.06] | unclear |
| Mistral | 8 | +2.31 [+1.71, +2.93] | deviates: real higher | −0.40 [−0.53, −0.27] | deviates: real lower |
| Mistral | 16 | +1.08 [+0.39, +1.72] | holds | −0.06 [−0.19, +0.07] | unclear |
| GPT | 4 (control) | +0.41 [−0.66, +1.42] | holds | −0.06 [−0.18, +0.06] | unclear |
| GPT | 8 | −2.10 [−3.09, −1.08] | deviates: real lower | +0.34 [+0.22, +0.48] | deviates: real higher |
| GPT | 16 | −1.43 [−2.48, −0.35] | unclear | +0.35 [+0.21, +0.48] | deviates: real higher |
| GPT | 32 | −2.01 [−3.38, −0.50] | deviates: real lower | +0.52 [+0.40, +0.64] | deviates: real higher |

**Frozen rule coverage.** Share of observed decisions whose full state the frozen rule found in the same card's table, and the additional share found only in the model-pooled table (after the card's table had no entry):

| n | Mistral, same card | Mistral, only pooled | GPT, same card | GPT, only pooled |
|---|---|---|---|---|
| 4 | 0.970 | 0.030 | 0.952 | 0.035 |
| 8 | 0.959 | 0.037 | 0.953 | 0.043 |
| 16 | 0.969 | 0.030 | 0.874 | 0.101 |
| 32 | — | — | 0.811 | 0.072 |

The rest backed off to coarser states; the largest such share was 0.116 (GPT, n = 32).

**Leave-one-size-out analysis (held-out-size check of Experiment D; exploratory).** Absolute error of the collapse share at round 8 for the held-out group size, with trajectory RMSE in parentheses. Abbreviations:
- **R3 frozen:** the rule learned from groups of four only.
- **R3 all:** the same state, trained on all other sizes.
- **R4-count / R4-share:** R3 all plus the number or the share of zero-givers among the others.

| model, held-out n | observed | R3 frozen | R3 all | R4-count | R4-share |
|---|---|---|---|---|---|
| GPT 8 | 0.563 | 0.346 (2.14) | 0.180 (1.47) | 0.140 (1.26) | 0.179 (1.26) |
| GPT 16 | 0.479 | 0.345 (1.56) | 0.095 (0.33) | 0.216 (1.80) | 0.137 (1.23) |
| GPT 32 | 0.688 | 0.524 (2.19) | 0.390 (0.96) | 0.112 (1.12) | 0.142 (0.85) |
| Mistral 8 | 0.208 | 0.401 (2.52) | 0.314 (1.96) | 0.275 (1.70) | 0.295 (1.76) |
| Mistral 16 | 0.792 | 0.057 (1.68) | 0.031 (1.32) | 0.039 (1.42) | 0.023 (0.89) |

Mean over the five rows: R3 all 0.202, R4-count 0.156, R4-share 0.155. R4-share was chosen on the RMSE tie-break. The improvement over R3 all was 0.047; the pre-specified gate required 0.05, so the 64-agent test was not run.
