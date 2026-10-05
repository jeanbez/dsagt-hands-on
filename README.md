# DSAgt Exercise: Battery Cycling, Raw Logs to a Cycle-Life Model

This exercise starts where most machine-learning projects start: with raw instrument output that no model can read. A fast-charge cycle-life campaign ran 120 lithium-ion cells at three labs. The labs sent one HDF5 file with a group per cell, and a few pages of documentation. Your goal is a model that predicts a cell's cycle life from its first 100 cycles, the task of [Severson et al., Nature Energy 2019](https://doi.org/10.1038/s41560-019-0356-8).

There are no prompts to paste. You are the scientist who owns this data; the agent is your assistant. Each mission says what you need, what to deliver, and how a reviewer will judge it. How you ask for it is up to you. The data carry the defects a real multi-lab campaign does, and none is announced.

Along the way the exercise uses each part of DSAgt: the knowledge base (the labs' documentation), skills (finding one, using the built-in ones, and packaging your own), registered codes and execution records, the AIDRIN readiness check, observability (the session's traces in MLflow), and the Genesis datacard.

## What is real and what is made up

**Made up.** Every value in `cycler_raw.h5` comes from a seeded degradation model, not from a cycler. The consortium, the three labs, the operators (the names are invented; any resemblance to a real person is a coincidence), the campaign documents, and the defects and their rates were all written for this exercise. The model you train says nothing about real batteries.

**Real.** The prediction task, the end-of-life convention (80 % of nominal capacity), the cell type (1.1 Ah LFP/graphite, fast-charged), and the idea of predicting cycle life from early-cycle features follow Severson et al. (2019). The kinds of defects are ones real campaigns have: loggers that write a sentinel for a missing reading, buffers replayed after a restart, loose thermocouples, sites that export different units, tests stopped early, and personal names in metadata. DSAgt, AIDRIN, scikit-learn, and the Genesis datacard are the real tools, and what they report about the data is real measurement of these made-up values.

## Prerequisites

- [DSAgt](https://github.com/AI-ModCon/dsagt) installed (`pip install "git+https://github.com/AI-ModCon/dsagt.git"`) and an agent platform installed and **already authenticated**
- Python 3.12 or later; `h5py`, `pandas`, and `scikit-learn` come with dsagt

## Setup

```bash
dsagt init
```

At the menu, name the project `battery-life`, pick your agent, and keep the defaults (the AI-readiness check stays on, and the `genesis` skill catalog is selected). Then, from your clone of this repository, write the campaign's files into the project and start the session:

```bash
PROJ=~/dsagt-projects/battery-life
python scripts/make_dataset.py "$PROJ"
dsagt start battery-life
```

Run the script with the Python that has dsagt installed. It prints the two paths it wrote: `data/cycler_raw.h5` and `docs/`.

## What the labs sent

- `data/cycler_raw.h5` (about 200 MB): one group per cell, `/cells/BC-0001` to `/cells/BC-0120`. Each group holds eight per-cycle 1-D datasets (`cycle_index`, `timestamp`, `discharge_capacity`, `charge_capacity`, `avg_voltage`, `max_temperature`, `internal_resistance`, `ambient_humidity`) and one 2-D dataset, `discharge_curve`: each cycle's discharge curve, the capacity delivered at the 400 voltages in the file's root `voltage_grid`. The group's attributes describe the cell and the test. Cells ran for different numbers of cycles, so the groups have different lengths.
- `docs/`: the campaign protocol and a note from each lab.

## How to work

- Work one mission at a time, and read what the agent reports before moving on.
- Keep the file names the missions give; the review checks them.
- Ask for outcomes, as you would ask a colleague. Naming the tools is not needed; seeing which ones the agent reaches for is part of the exercise.
- When a result surprises you, ask why before accepting it. The agent can be confidently wrong, and the records it keeps are how you check it.
- If you fall behind, the facilitator has checkpoint files for the start of each mission.
- `facilitator/` holds the answers. Leave it closed until the session is over.

## Missions

### 1. From a raw file to a table

The labs want to know whether this file can go straight into training. Find out, and if it cannot, turn it into one table.

**Deliver:** a short assessment of the file, and `data/cycles_raw.csv`: one row per cycle, with the cell's ID, the eight per-cycle channels, and every group attribute as columns. The discharge curves stay in the HDF5 file.

**Accepted when:**
- the labs' documentation is searchable from the session, and the assessment cites it where it explains something in the data;
- before any converter is written, existing skills were searched for one that already does the job, and the result is reported;
- every value in the table is the value in the HDF5 file: nothing cleaned, nothing converted, no attribute left out;
- the conversion is a reusable, recorded step that someone else can rerun by name;
- the table's data quality is measured by a recorded run, and the assessment says what that measurement can and cannot see.

### 2. Make it trustworthy

Clean the table so that a model learns battery physics, not logger artifacts.

**Deliver:** `data/cycles_clean.csv`.

**Accepted when:**
- each (cell, cycle) appears once;
- a reading the logger could not take is a missing value, not a number;
- every cell's values are in Ah and °C, as the labs' documentation says to convert them;
- sensor glitches are removed without removing real degradation;
- each change is its own recorded step, and its effect on data quality is measured by a recorded run before and after, and reported before the next step starts.

### 3. A training table that is fair and safe to share

**Definitions:**
- **cycle life**: as the campaign protocol defines it;
- **features**: computed from the first 100 cycles only: the capacity fade slope over cycles 10 to 100, the mean maximum temperature, the mean internal resistance and its change, and the mean voltage;
- **life class**: `short` when cycle life is under 550 cycles, `long` otherwise;
- a cell without a cycle life stays out.

**Deliver:** `data/features.csv`, one row per cell, with `lab`, `operator`, the features, `cycle_life`, and `life_class`; and a readiness verdict.

**Accepted when:**
- columns that carry no information are identified and the reason is given;
- the verdict quantifies, each number from a recorded measurement run: the class balance, how well each lab is represented, whether the share of short-lived cells differs by lab, how strongly each feature relates to cycle life, and the re-identification risk of `operator` and `lab`;
- cycle life is comparable across labs, or the difference is traced to the data rather than assumed;
- the verdict says what must change before the table is shared, consistent with the campaign's data policy.

### 4. Train, and show that curation helped

**Deliver:** `models/cycle_life.joblib`, a random forest regressor that predicts cycle life from the numeric features; and the same model trained on features computed from `data/cycles_raw.csv` (`data/features_raw.csv`), not saved.

**Accepted when:**
- training is a recorded step;
- both models report 5-fold cross-validated R² and mean absolute percentage error;
- the curated model is the better one. If it is not, the cause is found in the records and fixed before hand-off; "use the uncurated data" is not an accepted answer.

### 5. Hand-off

A reviewer who was not in the room, and the labs running the next campaign, must be able to understand, trust, rerun, and reuse what you did.

**Deliver:**
- `data/genesis_datacard_features.md`: a Level 1 (discoverability) Genesis datacard for `data/features.csv` that carries the readiness findings; its validation is a recorded run with no findings;
- `audit/pipeline.sh`: the pipeline from `data/cycler_raw.h5` to the model, generated from the recorded runs, not written by hand;
- the readiness record: every data-quality and readiness measurement of the session, in the order it ran, with its file and values;
- `skills/battery-curation/`: a skill the labs can follow on their next campaign's file to get from the raw HDF5 to `cycles_clean.csv`, using the codes this session registered;
- `audit/session_report.md`: what the session cost and where it went, from its traces: tokens in and out, errors, the number of agent turns, and which mission used the most. Get the numbers yourself, in a terminal beside the session: `dsagt info battery-life` summarizes the traces, and `dsagt traces battery-life` opens them in the MLflow viewer. Then have the agent write the report from them.

## Review

A run is complete when these exist in the project:

1. `data/cycles_raw.csv`, `data/cycles_clean.csv`, `data/features.csv`, `data/features_raw.csv`.
2. `models/cycle_life.joblib`.
3. A knowledge-base collection holding the four documents in `docs/`.
4. `data/genesis_datacard_features.md`, and a record of its validation.
5. `audit/pipeline.sh`, generated from the records.
6. `skills/battery-curation/SKILL.md`.
7. `audit/session_report.md`.
8. One execution record in `trace_archive/` per conversion, cleaning, feature, and training run, and readiness measurements before and after each cleaning step.

## Cleanup

```bash
dsagt rm battery-life -y
```
