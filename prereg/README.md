# prereg/

Internal written plans (hypotheses, decision rules, analysis plan), written
before the data. Not a public registry.

These files are the authoritative copies. Until 2026-10-12 they lived only in
the orc workspace (`orc/data/projects/PublicGoods/workspace/`), which is
git-ignored. On 2026-10-12 they were copied here byte for byte (sha256 equal
before and after the copy):

| file | sha256 at copy |
|---|---|
| `prereg_pilot.md` | `979b6b66b9bbcdc3ed584bb75d9d32f8746d04fd01cc92ee8bc455c47b1d0c34` |
| `prereg_pilot_ek_yama.md` | `e27c947a6132942a48f9a3fb942d1842689bde6e87f76fe7b89fcc0789c0f05b` |
| `prereg_minipilot.md` | `b36c69f82e0d2ae6e35bdf7c0d412337c67a20a52012238ab770d41153541d2e` |
| `prereg_main.md` | `d36cb26cf5d612c950102a207b1fbcadf59491dc1d6eef4f0ac2b643f7b7d81c` |

`prereg_main.md` at copy time: approved 2026-10-11, with the dated amendment
"Ek — Aşama 0a sonucu (2026-10-11)". Stage 0a (format A) had run; stage 0b
and stage 1 had not.

Rules from here on:

- Edit only these copies. The workspace copies stay as they are.
- Every change is a dated amendment with its reason, committed on its own.
  Earlier text is not rewritten; `git diff` must show additions only.
- Source tags inside the files (e.g. `[T99]`, `[S0A]`) point to reports in the
  orc workspace.

## Which plan belongs to which study (added 2026-10-21)

| file | in the preprint (`paper/preprint_v1.md`) |
|---|---|
| `prereg_pilot.md`, `prereg_pilot_ek_yama.md`, `prereg_minipilot.md` | pilots before Study 1 |
| `prereg_main.md` | Study 1 (the "main experiment") |
| `prereg_expA.md` | Study 2 (Experiment A) |
| `prereg_expB.md` | Study 3 (Experiment B) |
| `prereg_expC.md` | Study 4 (Experiment C); plan and forecast also deposited on Zenodo before the main run: https://doi.org/10.5281/zenodo.23483296 |
| `prereg_expD.md` | the 64-agent test (Experiment D), stopped at its gate; no paid call was made |
| `prereg_dyn.md` | Section 7, macro structure (exploratory; existing data only) |

Exploratory analyses that extend a study are written as dated amendments in
that study's plan, before they were computed.
