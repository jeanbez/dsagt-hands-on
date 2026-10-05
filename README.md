# <img src="assets/icons/zap.svg" width="28" height="28" alt=""> DSAgt Hands-On

### Battery Cycling: Raw Logs to a Cycle-Life Model

This exercise starts where most machine-learning projects start: with raw instrument output that no model can read. A fast-charge cycle-life campaign ran 120 lithium-ion cells at three labs. The labs sent one HDF5 file with a group per cell, and a few pages of documentation. Your goal is a model that predicts a cell's cycle life from its first 100 cycles, the task of [Severson et al., Nature Energy 2019](https://doi.org/10.1038/s41560-019-0356-8).

> [!IMPORTANT]
> **There are no prompts to paste.** You are the scientist who owns this data; the agent is your assistant. Each mission says what you need, what to deliver, and how a reviewer will judge it. How you ask for it is up to you. The data carry the defects a real multi-lab campaign does, and none is announced.

## <img src="assets/icons/milestone.svg" width="22" height="22" alt=""> Missions at a Glance

| | Mission | You Deliver | DSAgt Parts You Will Use |
|---|---|---|---|
| 1 | [From a raw file to a table](#mission-1-from-a-raw-file-to-a-table) | `data/cycles_raw.csv` | <img src="assets/icons/book.svg" width="16" height="16" alt=""> knowledge base, <img src="assets/icons/plug.svg" width="16" height="16" alt=""> skill catalog, <img src="assets/icons/gear.svg" width="16" height="16" alt=""> registered codes, <img src="assets/icons/pulse.svg" width="16" height="16" alt=""> readiness check |
| 2 | [Make it trustworthy](#mission-2-make-it-trustworthy) | `data/cycles_clean.csv` | <img src="assets/icons/gear.svg" width="16" height="16" alt=""> registered codes, <img src="assets/icons/pulse.svg" width="16" height="16" alt=""> readiness check, <img src="assets/icons/book.svg" width="16" height="16" alt=""> knowledge base |
| 3 | [A training table that is fair and safe to share](#mission-3-a-training-table-that-is-fair-and-safe-to-share) | `data/features.csv` and a verdict | <img src="assets/icons/pulse.svg" width="16" height="16" alt=""> AIDRIN fairness and privacy metrics, <img src="assets/icons/book.svg" width="16" height="16" alt=""> knowledge base |
| 4 | [Train, and show that curation helped](#mission-4-train-and-show-that-curation-helped) | `models/cycle_life.joblib` | <img src="assets/icons/gear.svg" width="16" height="16" alt=""> registered codes, <img src="assets/icons/history.svg" width="16" height="16" alt=""> execution records |
| 5 | [Hand-off](#mission-5-hand-off) | datacard, pipeline, readiness record, skill, session report | <img src="assets/icons/id-badge.svg" width="16" height="16" alt=""> datacard, <img src="assets/icons/sync.svg" width="16" height="16" alt=""> pipeline reconstruction, <img src="assets/icons/package.svg" width="16" height="16" alt=""> skill packaging, <img src="assets/icons/graph.svg" width="16" height="16" alt=""> MLflow traces |

## <img src="assets/icons/alert.svg" width="22" height="22" alt=""> What Is Real and What Is Made Up

**Made up.** Every value in `cycler_raw.h5` comes from a seeded degradation model, not from a cycler. The consortium, the three labs, the operators (the names are invented; any resemblance to a real person is a coincidence), the campaign documents, and the defects and their rates were all written for this exercise. The model you train says nothing about real batteries.

**Real.** The prediction task, the end-of-life convention (80 % of nominal capacity), the cell type (1.1 Ah LFP/graphite, fast-charged), and the idea of predicting cycle life from early-cycle features follow Severson et al. (2019). The kinds of defects are ones real campaigns have: loggers that write a sentinel for a missing reading, buffers replayed after a restart, loose thermocouples, sites that export different units, tests stopped early, and personal names in metadata. DSAgt, AIDRIN, scikit-learn, and the Genesis datacard are the real tools, and what they report about the data is real measurement of these made-up values.

## <img src="assets/icons/checklist.svg" width="22" height="22" alt=""> Prerequisites

- [ ] [DSAgt](https://github.com/AI-ModCon/dsagt) installed: `pip install "git+https://github.com/AI-ModCon/dsagt.git"`
- [ ] An agent platform installed and **already authenticated** (Claude Code, Codex, Goose, opencode, or Cline)
- [ ] Python 3.12 or later; `h5py`, `pandas`, and `scikit-learn` come with dsagt
- [ ] A clone of this repository

## <img src="assets/icons/rocket.svg" width="22" height="22" alt=""> Setup

**1. Create the project.**

```bash
dsagt init
```

At the menu, name the project `battery-life`, pick your agent, and keep the defaults: the AI-readiness check stays on, and the `genesis` skill catalog is selected.

**2. Write the campaign's files into the project and start the session,** from your clone of this repository:

```bash
PROJ=~/dsagt-projects/battery-life
python scripts/make_dataset.py "$PROJ"
dsagt start battery-life
```

Run the script with the Python that has dsagt installed.

> [!NOTE]
> **Expect:** the script prints two paths, `data/cycler_raw.h5` (about 200 MB) and `docs/`, in a second or two, and your agent opens in the project directory with dsagt connected.

## <img src="assets/icons/package.svg" width="22" height="22" alt=""> What the Labs Sent

- **`data/cycler_raw.h5`** (about 200 MB): one group per cell, `/cells/BC-0001` to `/cells/BC-0120`. Each group holds eight per-cycle 1-D datasets (`cycle_index`, `timestamp`, `discharge_capacity`, `charge_capacity`, `avg_voltage`, `max_temperature`, `internal_resistance`, `ambient_humidity`) and one 2-D dataset, `discharge_curve`: each cycle's discharge curve, the capacity delivered at the 400 voltages in the file's root `voltage_grid`. The group's attributes describe the cell and the test. Cells ran for different numbers of cycles, so the groups have different lengths.
- **`docs/`**: the campaign protocol and a note from each lab.

## <img src="assets/icons/light-bulb.svg" width="22" height="22" alt=""> How to Work

- Work one mission at a time, and read what the agent reports before moving on.
- Keep the file names the missions give; the review checks them.
- Ask for outcomes, as you would ask a colleague. Naming the tools is not needed; seeing which ones the agent reaches for is part of the exercise.
- When a result surprises you, ask why before accepting it. The agent can be confidently wrong, and the records it keeps are how you check it.
- If you fall behind, the facilitator has checkpoint files for the start of each mission.
- `facilitator/` holds the answers. Leave it closed until the session is over.

---

## <img src="assets/icons/table.svg" width="22" height="22" alt=""> Mission 1. From a Raw File to a Table

> **Goal:** the labs want to know whether this file can go straight into training. Find out, and if it cannot, turn it into one table.

**Action Items:**

- [ ] Make the labs' documentation searchable from the session.
- [ ] Get an assessment of `data/cycler_raw.h5`: its structure, and whether it is ready to train on, citing the documentation.
- [ ] Before any converter is written, have the agent search the existing skills for one that already does the job.
- [ ] Get the file turned into `data/cycles_raw.csv`.
- [ ] Get the table's data quality measured.

**Deliver:** a short assessment of the file, and `data/cycles_raw.csv`: one row per cycle, with the cell's ID, the eight per-cycle channels, and every group attribute as columns. The discharge curves stay in the HDF5 file.

**Accepted When:**

- the labs' documentation is searchable from the session, and the assessment cites it where it explains something in the data;
- before any converter is written, existing skills were searched for one that already does the job, and the result is reported;
- every value in the table is the value in the HDF5 file: nothing cleaned, nothing converted, no attribute left out;
- the conversion is a reusable, recorded step that someone else can rerun by name;
- the table's data quality is measured by a recorded run, and the assessment says what that measurement can and cannot see.

> [!TIP]
> **What to Expect:**
> - The documentation becomes a knowledge-base collection; indexing it takes a minute or two the first time.
> - The skill search returns candidates, and you decide whether any fits.
> - The readiness check refuses the HDF5 file as it is. That is a finding, not an error.
> - `data/cycles_raw.csv` has about 115,000 rows and 18 columns, and a first quality report gives completeness, duplicity, and outlier scores.
> - The scores look good. Keep reading.

## <img src="assets/icons/shield-check.svg" width="22" height="22" alt=""> Mission 2. Make It Trustworthy

> **Goal:** clean the table so that a model learns battery physics, not logger artifacts.

**Action Items:**

- [ ] Decide, with the agent, which cleaning steps the data and the documentation call for, and ask for the plan before anything runs.
- [ ] Get each change made as its own recorded step.
- [ ] Read the data-quality change after each step before the next one starts.
- [ ] Check the result against every requirement below yourself.

**Deliver:** `data/cycles_clean.csv`.

**Accepted When:**

- each (cell, cycle) appears once;
- a reading the logger could not take is a missing value, not a number;
- every cell's values are in Ah and °C, as the labs' documentation says to convert them;
- sensor glitches are removed without removing real degradation;
- each change is its own recorded step, and its effect on data quality is measured by a recorded run before and after, and reported before the next step starts.

> [!TIP]
> **What to Expect:**
> - A plan with several stages, each a registered code with its own execution record.
> - A readiness report after each stage, so every change has a number attached to it.
> - The row count drops by a few hundred, not thousands.
> - Most scores improve. If one gets worse, ask why before you call it a mistake.

## <img src="assets/icons/law.svg" width="22" height="22" alt=""> Mission 3. A Training Table That Is Fair and Safe to Share

> **Goal:** one row per cell, ready to train on, and a verdict on whether it is fair across labs and safe to share.

**Definitions**

- **cycle life**: as the campaign protocol defines it;
- **features**: computed from the first 100 cycles only: the capacity fade slope over cycles 10 to 100, the mean maximum temperature, the mean internal resistance and its change, and the mean voltage;
- **life class**: `short` when cycle life is under 550 cycles, `long` otherwise;
- a cell without a cycle life stays out.

**Action Items:**

- [ ] Find out which columns carry no information, and why.
- [ ] Get `data/features.csv` built as a recorded step.
- [ ] Get the table assessed for class balance, lab representation, outcome by lab, feature relevance, and re-identification risk.
- [ ] Compare cycle life across the labs yourself.
- [ ] Read the campaign's data policy, and get a verdict on what must change before sharing.

**Deliver:** `data/features.csv`, one row per cell, with `lab`, `operator`, the features, `cycle_life`, and `life_class`; and a readiness verdict.

**Accepted When:**

- columns that carry no information are identified and the reason is given;
- the verdict quantifies, each number from a recorded measurement run: the class balance, how well each lab is represented, whether the share of short-lived cells differs by lab, how strongly each feature relates to cycle life, and the re-identification risk of `operator` and `lab`;
- cycle life is comparable across labs, or the difference is traced to the data rather than assumed;
- the verdict says what must change before the table is shared, consistent with the campaign's data policy.

> [!TIP]
> **What to Expect:**
> - A few constant columns, some of them left over from your own cleaning.
> - 114 cells in the table.
> - Short-lived cells are a minority, and one lab supplies most of the cells.
> - Cycle lives in the hundreds to low thousands of cycles in every lab. A lab whose cells all died at once is a finding to chase, not a fact to report.

## <img src="assets/icons/graph.svg" width="22" height="22" alt=""> Mission 4. Train, and Show That Curation Helped

> **Goal:** a model, and evidence that the curation was worth doing.

**Action Items:**

- [ ] Get a random forest regressor trained on the numeric features as a recorded step, and saved.
- [ ] Get the same features computed from the uncurated table, and the same model trained on them.
- [ ] Compare the two models' scores.
- [ ] If the curated model is not the better one, find out why before going on.

**Deliver:** `models/cycle_life.joblib`, a random forest regressor that predicts cycle life from the numeric features; and the same model trained on features computed from `data/cycles_raw.csv` (`data/features_raw.csv`), not saved.

**Accepted When:**

- training is a recorded step;
- both models report 5-fold cross-validated R² and mean absolute percentage error;
- the curated model is the better one. If it is not, the cause is found in the records and fixed before hand-off; "use the uncurated data" is not an accepted answer.

> [!TIP]
> **What to Expect:**
> - Two training records, each with R² and MAPE in its output.
> - The curated model clearly ahead: R² well above 0.5 and an error in the low tens of percent.
> - A curated model that ties or loses means a defect survived curation. The execution records and the stage files show which step let it through; fix that step and rerun from it.

## <img src="assets/icons/share.svg" width="22" height="22" alt=""> Mission 5. Hand-Off

> **Goal:** a reviewer who was not in the room, and the labs running the next campaign, can understand, trust, rerun, and reuse what you did.

**Action Items:**

- [ ] Get a Level 1 Genesis datacard for `data/features.csv` written and validated.
- [ ] Get the pipeline generated from the recorded runs.
- [ ] Get the readiness record of the whole session.
- [ ] Get the curation packaged as a skill for the next campaign.
- [ ] In a terminal beside the session, run `dsagt info battery-life` and `dsagt traces battery-life`, then have the agent write the session report from what they show.

**Deliver**

- `data/genesis_datacard_features.md`: a Level 1 (discoverability) Genesis datacard for `data/features.csv` that carries the readiness findings; its validation is a recorded run with no findings;
- `audit/pipeline.sh`: the pipeline from `data/cycler_raw.h5` to the model, generated from the recorded runs, not written by hand;
- the readiness record: every data-quality and readiness measurement of the session, in the order it ran, with its file and values;
- `skills/battery-curation/`: a skill the labs can follow on their next campaign's file to get from the raw HDF5 to `cycles_clean.csv`, using the codes this session registered;
- `audit/session_report.md`: what the session cost and where it went, from its traces: tokens in and out, errors, the number of agent turns, and which mission used the most.

> [!TIP]
> **What to Expect:**
> - The datacard's validator reports no findings, and its run is in `trace_archive/`.
> - `audit/pipeline.sh` lists your codes in the order they ran, failed attempts as comments.
> - The readiness record has one row per measurement, from the raw file to the training table.
> - `dsagt info` lists `battery-curation` among the project's skills.
> - `dsagt traces` opens the MLflow viewer on the session's traces: one per agent turn and one per code run. Most input tokens are the agent re-reading its own context.

---

## <img src="assets/icons/tasklist.svg" width="22" height="22" alt=""> Review

A run is complete when these exist in the project:

- [ ] `data/cycles_raw.csv`, `data/cycles_clean.csv`, `data/features.csv`, `data/features_raw.csv`
- [ ] `models/cycle_life.joblib`
- [ ] a knowledge-base collection holding the four documents in `docs/`
- [ ] `data/genesis_datacard_features.md`, and a record of its validation
- [ ] `audit/pipeline.sh`, generated from the records
- [ ] `skills/battery-curation/SKILL.md`
- [ ] `audit/session_report.md`
- [ ] one execution record in `trace_archive/` per conversion, cleaning, feature, and training run, and readiness measurements before and after each cleaning step

## <img src="assets/icons/trash.svg" width="22" height="22" alt=""> Cleanup

```bash
dsagt rm battery-life -y
```
