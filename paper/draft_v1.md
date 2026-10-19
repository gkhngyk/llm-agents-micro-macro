# What LLM agents say they would do does not predict what their groups do — a rule learned in play does

*A pre-registered, prospectively tested public goods study with three large language models*

**Draft v1 (2026-10-19). Not for circulation.** Every number below is generated from the result files by `paper/paper_numbers.py` (output `paper/numbers.md`). References marked ✓ were checked against Crossref, arXiv or Zenodo on 2026-10-19.

Gökhan Geyik (Empler AI)

---

## Abstract

LLM agents are increasingly used as stand-ins for human participants in simulated societies. Two practices are common: agents are given identity descriptions ("personas"), and their behaviour is calibrated or validated with one-shot questions about what they would do. We test both in a repeated public goods game (groups of four, 20 points, MPCR 0.4) with three models (DeepSeek-V4.1-Flash, Mistral-Large-4, GPT-6-Luna), following written plans fixed before the data. **Study 1** (504 groups, 23,040 answers) crossed four cities with three description styles. City names alone changed nothing (largest pair difference 2.2 points of 20). Value sentences produced differences of up to 14.5 points whose direction followed the wording of the sentence, not the cities' human ranking; models often read the card as a cue from the experimenter. Groups contributed less than a simulation built from each agent's stated response to an isolated question predicted (13 of 36 cells below, none above). **Exploratory analyses** traced this gap to the measurement context: a simple rule learned from in-game decisions (own last contribution, others' last average, whether someone gave 0, rounds left) reproduced group trajectories in cross-validation (trajectory RMSE 0.41–0.58 vs 2.01–3.76 for the stated responses) and in an independent new run (0.41–0.76 vs 2.10–4.34). **Study 2** tested our exploratory mechanism — that seeing an individual free rider triggers collapse — by hiding individual contributions; it held only for DeepSeek. **Study 3** froze the learned rule before a new 15-round game and predicted it prospectively: the forecast held in all three models (mean error −0.06 to +0.82 points), and agents tracked the announced horizon rather than the round numbers seen in training. The message for agent-based simulation is practical: what an LLM agent says in isolation is a poor model of what it does in a group; rules measured in context are a good one.

---

## 1. Introduction

Generative agent-based models (GABMs) replace hand-coded behavioural rules with language models prompted to play a role. Two questions decide whether such simulations tell us anything: do the identities we give agents produce the behaviour we attribute to those identities, and can the collective behaviour of a population be understood from the behaviour of its members?

For humans, the second question has a classic answer in the public goods game. Fischbacher, Gächter and Fehr (2001) ✓ elicited *contribution schedules* — what a person contributes for each possible average contribution of the others — and found most people to be conditional cooperators. Fischbacher and Gächter (2010) ✓ showed that such schedules, together with beliefs, account for the decline of cooperation in repeated play. Stated conditional rules thus connect the individual to the group.

For LLM agents the evidence is mixed. Large studies report that collective outcomes can look human-like while the underlying decision rules do not (Ferraz de Arruda et al., 2026 ✓), that agreement with human data is confined to starting points (Tareaf, 2026 ✓), that smaller models behave as static players without within-game updating (Teo, 2026 ✓), and that personas can override explicit payoffs (Manoranjan & Gaikwad, 2026 ✓) or transfer only through words that map onto actions (Wang, Lester & Srivastava, 2026 ✓). In earlier work we found that the *wording* of an identity description, not the culture it names, set LLM agents' behaviour in the ultimatum game (Geyik, 2026 ✓).

Here we ask both questions in one design and test the answers forward in time:

1. **Identity.** Do city names, value sentences and institutional facts about the same four cities change contributions, and do the differences follow the human cross-cultural ranking (Herrmann, Thöni & Gächter, 2008 ✓)?
2. **Interaction.** Does play in a group enlarge, dampen or preserve those differences?
3. **Micro to macro.** Does a group simulated from each agent's stated response to an isolated question reproduce the real group? If not, does a rule learned in play — and frozen — predict a new game?

Our contributions: (i) identity effects come from the wording of value sentences, not from cities, and models frequently treat the description as an instruction; (ii) one-shot stated responses mispredict group dynamics in all three models; (iii) a minimal in-context rule closes the gap and, frozen in advance, predicts a game of unseen length; (iv) a pre-registered test rejected our own exploratory mechanism for two of three models. All plans, amendments, code, data and reasoning texts are open.

## 2. Method

### 2.1 Game and models

Groups of four homogeneous agents (all four receive the same identity card) play a linear public goods game: each round every player receives 20 points and contributes a whole number from 0 to 20; each contributed point yields 0.4 points to each player. Players see every player's contribution and their own earnings after each round. There is no punishment. Before play, each agent answers two rule-check questions (correct answers 28 and −6).

Three models were pinned to one provider each through OpenRouter: `deepseek/deepseek-v4.1-flash` (DeepInfra, fp8), `mistralai/mistral-large-4-0` (Mistral), `openai/gpt-6-luna` (OpenAI); model snapshots were logged on every call and did not change across the studies. Temperature and reasoning effort were left at provider defaults; `max_tokens` was 16,000. Answers were requested as a JSON object with a contribution and a one- or two-sentence rationale; invalid answers were re-requested and counted, never coded.

### 2.2 Identity cards

Twelve cards: four cities (Boston, Copenhagen, Athens, Riyadh) × three styles. *Minimal:* "You are a 21-year-old university student living in {city}." *Value:* minimal + one value sentence (e.g. Boston: "Where you grew up, people prize personal liberty and speaking up against authority."; Riyadh: "…people strongly respect family elders and tribal leaders."). *Factual:* minimal + "In your country, a lawsuit over an unpaid bill takes about N days" (World Bank Doing Business 2020 contract-enforcement time: 444, 485, 1,711, 575). The system message read "The following describes you:" followed by the card. Cities were chosen so that their human ranking in Herrmann et al. (2008) is known (rounds 1–10: Copenhagen > Boston > Riyadh > Athens).

### 2.3 Isolated question

In a separate arm, agents with the same card answered single questions: "This is round 5 of 10. In the previous round the other 3 players of your group contributed, on average, X points each" for X ∈ {0, 5, 10, 15, 20}, four repetitions. This is the stated response, analogous to a contribution schedule.

### 2.4 Process

For every study a written plan (hypotheses with both directions, decision rules, analysis code tested on synthetic data) was committed before any paid call; analysis scripts refuse to run on incomplete data. Deviations and exploratory analyses are recorded as dated amendments, written before they were computed. These are internal written plans in a public repository, not entries in a public registry. A difference counts as present ("var") when its point estimate exceeds 2 points and its group-level bootstrap 95% CI excludes 0 (10,000 resamples; Holm correction within model and hypothesis family where a family has several tests). The research was carried out with an AI assistant (Claude) under the author's direction; every number was regenerated from the result files and the key ones were recomputed with independent code.

## 3. Study 1: identity, interaction and the stated-response gap

**Design.** 12 cards × 3 models; 16 groups per cell for DeepSeek and GPT, 10 for Mistral (504 groups, 10 rounds), plus 144 isolated schedules; 23,040 answers; 45.34 USD. Rule checks were answered correctly by 816/816 (DeepSeek), 528/528 (Mistral) and 811/816 (GPT) agents.

### 3.1 City names do nothing; value sentences do a lot, along their wording

With minimal cards no city pair differed in any model (largest |difference| 1.02, 1.54 and 2.22 points; none "var"). Value sentences moved contributions far more than cities did (Table 1). In DeepSeek and Mistral the Boston value card ("personal liberty and speaking up against authority") produced near-zero contributions (0.15 and 0.20 of 20 over ten rounds) and the Riyadh value card ("respect family elders and tribal leaders") the highest of all cards (13.06 and 14.65). The resulting Boston − Riyadh difference (−12.92 and −14.45) runs against the human ranking (Boston > Riyadh). Across the six pre-specified city pairs, value cards produced the human direction in 3, 2 and 3 pairs and the reverse direction in 2, 3 and 0 pairs (DeepSeek, Mistral, GPT). Only one pair (Copenhagen − Boston) received the same label in all three models; GPT's differences were small (at most 2.38).

**Table 1.** Mean contribution over ten rounds (of 20), value and minimal cards.

| | Boston | Copenhagen | Athens | Riyadh |
|---|---:|---:|---:|---:|
| DeepSeek, minimal | 0.61 | 1.62 | 1.47 | 1.45 |
| DeepSeek, value | 0.15 | 9.26 | 1.94 | 13.06 |
| Mistral, minimal | 6.03 | 7.56 | 6.76 | 7.29 |
| Mistral, value | 0.20 | 10.11 | 10.41 | 14.65 |
| GPT, minimal | 7.81 | 8.17 | 7.90 | 5.96 |
| GPT, value | 8.91 | 11.28 | 9.08 | 9.25 |
| Human N→P, rounds 1–10 (Herrmann et al.) | 9.33 | 11.53 | 6.36 | 7.63 |

The factual court-time sentence mattered only for Mistral, which read Athens' 1,711 days as "no enforcement" and contributed 1.59 against 5.51–7.81 for the other factual cards (human-direction differences of 5.75, 6.22 and 3.93 in the three Athens pairs). The one pair in which the fact and the human ranking point in opposite directions (Copenhagen − Boston, 485 vs 444 days) showed no difference in any model.

Reasoning texts explain the value effects. Models first derive that contributing 0 maximises their payoff, then use the card to decide whether to deviate, and they frequently describe the card as a cue from the experimenter (DeepSeek, Copenhagen value, round 10: "This is a direct hint about the decision. If they wanted pure rationality, they wouldn't include that."; DeepSeek, Riyadh value: "If I choose 0, I might fail the cultural manipulation check."). "Equal standing" became a rule to contribute the same as everyone else; Mistral added stereotypes absent from the card (Arabic honour and shame terms in 13 of 16 sampled Riyadh records). DeepSeek and Mistral recognised the game and its literature in 97% and 100% of decisions (paradigm or author names in their reasoning; GPT's rationales, 0%).

### 3.2 Interaction: model-dependent, and in GPT entirely an end-game effect

Of 36 pre-registered interaction tests (12 pairs × 3 models; growth Δ = |D(10)| − |D(1)|), 4 differences grew, 10 faded and 22 were preserved. Fading in DeepSeek partly reflects a floor: in factual cells all its groups contributed 0 in round 10. In GPT, the two "growing" value pairs grew only in the last round (Copenhagen − Athens: D(9) = 1.97, D(10) = 6.88): with most cards GPT agents defected in round 10, with the Copenhagen and Riyadh value cards they did not (57 and 51 of 64 round-10 decisions at ≥ 10, against 2–21 for the other cards). Model consistency was low (same label in all three models: 1 of 6 value pairs, 2 of 12 interaction tests).

### 3.3 The stated-response gap

For each cell we simulated, from each real group's round-1 contributions, a group in which every agent follows its own stated response (linear interpolation of the isolated answers; no interaction beyond the previous round's average). Real groups contributed less than these simulations in 13 of 36 cells and more in none (mean gap −1.64, −1.53, −2.17 points; negative in 32 of 36 cells). The stated responses were close to "give what the others gave" (GPT's average stated response equalled X at every point in 10 of its 12 cells). The gap persisted for DeepSeek and Mistral when the last two rounds were excluded (rounds 2–8: 3 and 5 cells below; GPT 0).

## 4. Exploratory analyses: where the gap comes from

These analyses were designed after the Study 1 results and are labelled exploratory; each was written down before it was computed.

### 4.1 Reading and counting

Two regularities stood out. First, contributions were almost exclusively focal: 96.0% of the 20,160 group-round decisions were exactly 0, 10 or 20. Second, a visible zero-contributor was followed by defection. Among decisions where the agent had itself contributed ≥ 10 in the previous round and the others' average was ≥ 5, the agent contributed 0 in 65% (DeepSeek), 61% (Mistral) and 15% (GPT) of cases when one of the others had given 0, against 2%, 3% and 0% when none had. The isolated question shows only an average, so a simulation from it cannot represent this.

### 4.2 Learning the rule in play

We learned empirical, stochastic decision rules from the group data, keeping the 0/10/20 discreteness: in each state an agent draws one of the real decisions observed in that state. States combined the agent's own previous contribution (5 bins), the others' previous average (6 bins), whether one of the others gave 0 (R2) and the rounds left (R3: ≥ 2 left, second-to-last, last). Rules were evaluated by leave-one-group-out cross-validation in Study 1 and, without refitting, on the independent arm-B groups of Study 2 (same prompt, new run four days later).

**Table 2.** Trajectory RMSE (points), stated response (R0) vs rules learned in play.

| | R0 stated | R1 own + others | R2 + zero | R3 + rounds left |
|---|---:|---:|---:|---:|
| DeepSeek, Study 1 (cross-validated) | 2.01 | 0.76 | 0.66 | **0.41** |
| Mistral, Study 1 | 3.76 | 2.05 | 2.03 | **0.58** |
| GPT, Study 1 | 3.04 | 1.83 | 1.81 | **0.44** |
| DeepSeek, new run | 2.10 | 0.42 | 0.40 | **0.41** |
| Mistral, new run | 4.34 | 3.14 | 3.17 | **0.76** |
| GPT, new run | 2.83 | 2.16 | 2.00 | **0.67** |

R3 matched every one of the 36 Study 1 cells and the 12 new-run cells (no cell above or below). What was missing differed by model: for DeepSeek, in-game behaviour itself (R1 already sufficed; in play DeepSeek is far less cooperative than its stated "match the others"), for Mistral and GPT the horizon (without the rounds-left state, simulations stayed above the real groups). The zero indicator added little on aggregate (R1 → R2).

## 5. Study 2: does seeing the free rider cause the collapse?

The counting in 4.1 suggested a mechanism. We tested it with a pre-registered manipulation of feedback: arm B showed every player's contribution (the Study 1 prompt, byte-identical to 60 sampled Study 1 prompts); arm T showed only the agent's own contribution and the others' average. Four minimal cards; 12, 8 and 12 groups per cell (256 groups); 23.81 USD. Arm B reproduced the Study 1 minimal cells in 11 of 12 cells (|difference| ≤ 2).

The primary hypothesis — visibility speeds the collapse (rounds 2–9, T − B > 2) — was not supported in any model: DeepSeek +0.43 [−0.21, +0.98] (equivalent to no difference), Mistral −1.65 [−3.12, −0.14], GPT −1.98 [−3.55, −0.42]; the latter two point the other way but stay below the 2-point threshold. The mechanism test (share of 0 after a zero-contributor, same true state in both arms) supported the mechanism only for DeepSeek (0.88 with visible zeros vs 0.58 without, −0.31 [−0.53, −0.08]); Mistral (0.60 vs 0.56) and GPT (0.13 vs 0.04) did not differ. Without individual information Mistral groups decayed faster (round 9: 5.1 in B, 2.1 in T): a lower average was enough to make everyone reduce. GPT differed already in round 1, before any feedback (−1.77 [−3.12, −0.42]): the rewording of a single rule sentence ("you are told … the average contribution of the other 3 players") lowered its opening contribution.

## 6. Study 3: predicting a game the rule has never seen

To test the learned rule forward, we froze R3 (tables learned from Study 1 only; file hash in the plan) and computed, before any call, its forecast for a 15-round game; the prompt differed from Study 1 only in the number of rounds. A rival variant, R3-absolute, maps rounds by their absolute number as in training (rounds 9 and 10 as end game), and predicts an early collapse. Eight cards (minimal and value), 8, 6 and 8 groups per cell (176 groups); 23.08 USD billed.

**Pre-registered results.** Starting each group from its observed round 1, the frozen rule predicted rounds 2–15 within the equivalence band in all models (Table 3), with 23 of 24 cells consistent. In rounds 9–13 the absolute-round variant was wrong by +4.38 (Mistral) and +6.87 (GPT) points — real groups did not collapse early — so Mistral and GPT "track the announced horizon"; for DeepSeek the same error was smaller (+1.49 [+0.82, +2.18]) and the test did not discriminate. GPT's real groups stayed at about 11 until round 14 and dropped to 4.0 in round 15.

**Table 3.** Study 3: observed minus predicted (rounds 2–15) and trajectory RMSE.

| | B-H1 Δ [95% CI] | label | RMSE R3 | R3-absolute | R1 | R0 stated |
|---|---|---|---:|---:|---:|---:|
| DeepSeek | −0.06 [−0.60, +0.48] | holds (tight) | **0.37** | 1.35 | 0.81 | 1.83 |
| Mistral | +0.82 [+0.17, +1.52] | holds | **0.89** | 3.13 | 2.82 | 2.29 |
| GPT | +0.67 [−0.17, +1.46] | holds | **0.77** | 5.29 | 2.92 | 2.36 |

The unconditional forecast written before the run (round 1 drawn from Study 1) had RMSE 0.53, 0.45 and 2.19. GPT's larger error comes from round 1: in the longer game GPT opened higher (12.1) than in Study 1 (forecast 9.8) — a longer horizon raised initial cooperation, which the rule, given round 1, does not have to explain.

## 7. Discussion

**Stated responses are a poor model of LLM agents in groups.** Human contribution schedules connect individual and group (Fischbacher & Gächter, 2010). For LLM agents a one-shot question about "round 5 of 10" did not: the agent's answer in isolation differed from its behaviour in play (DeepSeek), and missed the role of the horizon (Mistral, GPT). This is a stated-versus-revealed gap with a direct methodological consequence: calibrating or validating GABM agents with isolated questions can misstate collective dynamics even when each answer looks sensible.

**Rules measured in context are a good model.** A rule with one round of memory, the others' average and the rounds left reproduced group trajectories, generalised to a new run and, frozen, predicted a game of unseen length. In complexity terms the macro dynamics here are not irreducible: they follow from micro rules, provided the rules are measured where they operate. This complements reports of macro–micro dissociation (Ferraz de Arruda et al., 2026): aggregate fit does not guarantee the right micro rules, and, as we show, the right micro rules require measuring in context.

**Identity descriptions act as instructions.** City names did nothing; value sentences acted through their wording ("equal standing" → equal contributions; "liberty and speaking up against authority" licensed keeping one's points), consistent with behavioural anchors (Wang et al., 2026) and with our ultimatum-game results. Models said so: they treated the card as a hint from the experimenter. Claims that LLM populations simulate cultures should be tested against this alternative.

**Our own mechanism failed a fair test.** The "visible free rider" account, natural after reading the transcripts, held for one model only. The stronger account — rules in context, including the horizon — survived a prospective test.

### Limitations

Groups were small (four agents), homogeneous and played at most 15 rounds, without networks or punishment. Three proprietary or provider-served models were used; providers intervened in ways we could only document (Mistral's provider added a system instruction about JSON output that the model quoted in 68 of 600 Study 0b reasoning texts; DeepSeek's provider imposed rate limits; one Mistral outage interrupted Study 3). DeepSeek contributed near the floor with minimal cards, which limits several of its tests, and its long reasoning reached the token cap in many groups, which makes one pre-registered sensitivity analysis uninformative for it. The learned rule was designed after Study 1; Study 3 tests it prospectively but only for a longer horizon of the same game. The models recognise the game and its literature, so "human-like" behaviour may be reproduced knowledge. Comparisons with human data are directional only.

## 8. Data and code availability

Plans and amendments (`prereg/`), code, configurations, frozen rule tables and forecasts (`data/expB/`), analysis outputs and all decisions with reasoning texts are in the project repository; raw API logs are released in redacted form (they contain an account identifier). [Repository and Zenodo DOI to be added.]

## References

- Fischbacher, U., Gächter, S., & Fehr, E. (2001). Are people conditionally cooperative? Evidence from a public goods experiment. *Economics Letters*, 71, 397–404. https://doi.org/10.1016/S0165-1765(01)00394-9 ✓
- Fischbacher, U., & Gächter, S. (2010). Social preferences, beliefs, and the dynamics of free riding in public goods experiments. *American Economic Review*, 100, 541–556. https://doi.org/10.1257/aer.100.1.541 ✓
- Ferraz de Arruda, H., Gracia Lázaro, C., Aleta, A., & Moreno, Y. (2026). Collective cooperation without individual fidelity in LLM agents. arXiv:2606.30454 ✓
- Geyik, G. (2026). LLMs simulate the description of a culture, not the culture: An attempt to reproduce Henrich's cross-cultural ultimatum game finding with LLM agents. Zenodo. https://doi.org/10.5281/zenodo.23119302 ✓
- Herrmann, B., Thöni, C., & Gächter, S. (2008). Antisocial punishment across societies. *Science*, 319, 1362–1367. https://doi.org/10.1126/science.1153808 ✓
- Manoranjan, V., & Gaikwad, S. N. S. (2026). When identity overrides incentives: Representational choices as governance decisions in multi-agent LLM systems. arXiv:2601.10102 ✓
- Tareaf, R. B. (2026). Benchmarking large language model agent societies against human behavioural distributions. arXiv:2608.28182 ✓
- Teo, P. H. (2026). LLM agents as static level-k players in behavioural games. arXiv:2606.27845 ✓
- Wang, Y., Lester, J., & Srivastava, S. (2026). The story shapes the agent: Narrative priors in LLM behavior. arXiv:2607.18566 ✓
- World Bank (2020). Doing Business 2020. [to be checked]

---

### Open items before circulation

1. Check the human N→P city means against the published data file (computed values; Table 1 last row).
2. Verify the AgentSociety2 public-goods example (reported to show the opposite gap) from its primary source before citing.
3. Figures: trajectories per model (Study 1 observed vs R0 vs R3; Study 3 observed vs frozen forecast vs R3-absolute).
4. Release redacted raw logs; add repository and DOI.
5. Decide venue and length; this draft is a full-length version.
