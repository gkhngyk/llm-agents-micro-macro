# Literature scan for the next study — 2026-10-03

Question scanned: "Can LLM agents that are wrong at the micro level still
produce the right macro outcome? Does description sensitivity leak into
collective dynamics?" — proposed paradigm: repeated public goods game (PGG)
with and without punishment.

Method: web search + arXiv abstracts only (no full texts read). Coverage is
therefore incomplete; the four closest papers must be read in full before
any design is fixed.

## Verdict

The idea as first stated is largely taken. Its three building blocks were
each published in 2026:

| Building block | Already shown by |
|---|---|
| LLM groups do not reproduce the human decay of PGG contributions; punishment does not raise (often lowers) contributions | Bin Tareaf, SILICA, arXiv:2608.28182 (12 open models, human anchors); Teo, arXiv:2606.27845 (flat or rising contributions at every model scale; includes framing and base-vs-instruct factors); Piedrahita et al., arXiv:2506.23276; Li & Shirado, arXiv:2502.17720 |
| Macro can look human while micro is wrong ("macro–micro dissociation") | Arruda, Gracia-Lázaro, Aleta, Moreno, arXiv:2606.30454 (networked Prisoner's Dilemma vs. a large human experiment: macro decay reproduced, heterogeneity and conditional cooperation not) |
| Results change under perturbations that leave the rules untouched / prompt sensitivity of macro outcomes in GABM | SILICA (apparatus perturbations, e.g. action order costs 58 points); Williams & Hosseinichimeh, arXiv:2608.26221 (epidemic GABM: synonymous prompts no effect, non-synonymous and contextual changes shift the macro curve) |
| Interaction amplifies or overturns individual-level biases; group-size effects | Flint, Aiello, Pastor-Satorras, Baronchelli, PNAS 2026 (arXiv:2510.22422) |
| Wording of persona/narrative drives behaviour through "anchor words" | Wang, Lester, Srivastava, arXiv:2607.18566 (narrative priors; removing anchor words cuts persona transfer by 95 %) — parallels our description test |
| Personas override explicit payoffs in 4-agent games | Manoranjan & Gaikwad, arXiv:2601.10102 |
| GABM validation on social-dilemma paradigms | Cross, Haber, Yamins, arXiv:2507.22049; Willis et al., arXiv:2602.16662; Vallinder & Hughes, arXiv:2412.10270; Akata et al., arXiv:2305.16867 |

## What still looks open (from abstracts only)

A. **Propagation of description sensitivity through interaction.** No paper
   found that takes a controlled *identity-description* manipulation, measures
   the induced difference at the micro level (isolated decision / elicited
   strategy) and at the macro level (group end-state), and reports the ratio —
   i.e. whether interaction amplifies or damps description-induced differences,
   and how that depends on group size, horizon or network. SILICA perturbs the
   apparatus, not the identity; Williams & Hosseinichimeh vary prompts in a
   model with little strategic interaction; Flint et al. study model biases,
   not prompt-induced ones.

B. **Second cross-cultural paradigm with a description test.** No LLM
   replication found of Herrmann, Thöni & Gächter (2008, 16 participant pools,
   antisocial punishment) that varies the identity description. This is the
   direct extension listed as future work in our paper.

## Risks

- The field moved fast in 2026; anything in A or B may appear within months.
- Teo reports flat or rising LLM contributions: if dynamics are flat,
  description-induced differences may simply persist (ratio ≈ 1), a valid but
  less striking result.
- Abstract-level scan: a full-text read of SILICA, Teo, Arruda et al. and
  Flint et al. is needed to confirm A is really open.

## Full-text read of the four closest papers — 2026-10-03

Each paper's full text was read by a separate reader with the same question
list; key claims were then spot-checked against the extracted text.

| Paper | Identity/persona given to agents? | Same manipulation measured in isolation AND after interaction? | Relevant result |
|---|---|---|---|
| SILICA (arXiv:2608.28182) | Yes, minimal "plain persona"; varied in layout (sentence/bullets/table) and content (self-interested vs prosocial) | **No** — no isolated-agent arm; effects reported only on whole-run outcomes | PGG (4 agents, 10 rounds, anchors Fischbacher 2001, Fehr & Gächter 2000): round-1 contributions match humans in 8/11 models, round-10 in 0/11; 7 models end higher than they start, 1 declines. Punishment lowers final contributions in 4/9 models. A self-interested persona removes cooperation entirely in two models. 12 open models ≤ 32B. |
| Teo (arXiv:2606.27845) | No persona ("You are participant P1"); identical agents | **No** | PGG after Herrmann et al. 2008, but only the St. Gallen pool as anchor (no cross-cultural comparison). Human slope −0.91 tokens/round; LLM slopes +0.13 to +0.24 at every scale. Game-context framing (neutral/cooperative/competitive): no main effect. Instruct models open higher than base. Antisocial punishment targeting already in round 1. Single family (Qwen 2.5, ≤ 32B). Calls for heterogeneous agents. |
| Arruda et al. (arXiv:2606.30454) | Minimal factual tags (student, gender) | **No** — personas compared at macro level only | Networked PD vs Gracia-Lázaro et al. 2012. Macro decay matched only by the one model selected for its macro fit (of nine); heterogeneity and conditional cooperation not matched. Persona tags and temperature did not qualitatively change results. No mechanism analysis; lists "broader prompt and model robustness" and other dilemmas as future work. |
| Flint et al. (arXiv:2510.22422, PNAS 2026) | Deliberately none; one prompt template; homogeneous populations | Isolated bias vs collective outcome is the core comparison, but the varied factor is model × word pair, **not** prompt or description | Naming game: interaction amplifies, induces or reverses individual word biases; depends nonlinearly on group size (critical N). Method: extract the isolated response policy, predict collective dynamics, compare with simulation. No human benchmark. |

### Conclusions

1. Question A (does interaction amplify or damp identity-description-induced
   differences?) is **not answered by any of the four**. Open, confirmed at
   full-text level for these papers.
2. Also open in all four: heterogeneous groups (every study uses identical
   agents within a group), frontier/closed models (all use open models
   ≤ 32–70B, mostly ≤ 32B), cultural identities, and the value-laden /
   minimal / factual wording contrast.
3. Question B (cross-cultural PGG, 16 pools of Herrmann et al. 2008, with a
   description test) is not done by Teo, who uses the same game but one pool.
4. Prior that lowers the expected payoff of A: LLM PGG trajectories are flat
   or rising with little within-model variance, and agents look "static"
   (weak belief updating). The likely result is "differences are preserved
   (ratio ≈ 1)" unless the description creates conditional or punitive
   behaviour that feeds back — which our value-laden cards did produce in
   one-shot play.
5. Method worth adopting (from Flint et al.): measure each description's
   isolated response function (including responses conditioned on others'
   contributions, i.e. the strategy method), build a no-interaction null
   prediction for the group, compare it with the observed group outcome,
   and vary group size.
6. Description content is already known to matter in groups (SILICA:
   self-interested vs prosocial persona); the novelty of A is the micro vs
   macro comparison and the human cultural anchor, not "persona matters".

Caveats: SILICA's supplementary information and the PNAS final version of
Flint et al. were not available in the files read; a few phrases relayed by
the readers could not be matched verbatim in the text and are not quoted here.
