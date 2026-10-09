# Battery Cycling: Facilitator Reference

The answers to the [battery-cycling exercise](../README.md): for each mission, a reference prompt, what dsagt should do without being asked, a hint for a group that is stuck, and the values a correct run produces. Participants get the exercise README, not this file. The session plan is [TUTORIAL_PLAN.md](TUTORIAL_PLAN.md).

## Tools

- **Checkpoints.** `facilitator/scripts/reference_pipeline.py <project>/data` writes `cycles_raw.csv`, `cycles_clean.csv`, `features.csv`, and `features_raw.csv` from `cycles_raw.h5`, and prints the reference model scores. A group that fell behind copies the file the next mission starts from.
- **Dry run.** The reference prompts below run headless, the way a participant's session would go if they asked exactly this. The driver is `tests/headless_usecases.py` in a checkout of the [dsagt repository](https://github.com/AI-ModCon/dsagt); `HANDS_ON` is this repository's directory, and `--agent` is `claude` or `codex`:

  ```bash
  dsagt init battery-ref --agent claude
  python "$HANDS_ON/scripts/make_dataset.py" ~/dsagt-projects/battery-ref
  cd <dsagt checkout>
  uv run --no-sync python tests/headless_usecases.py "$HANDS_ON/facilitator" battery-ref
  ```

  The log is `~/dsagt-projects/battery-ref/headless.log` unless `--log` names another path. The session report (mission 5) needs a person at a terminal and is not part of the dry run.

## DSAgt coverage

| DSAgt part | Where the exercise uses it | Missions |
|---|---|---|
| Knowledge base (`kb_ingest`, `kb_job_status`, `kb_search`) | The labs' documentation explains the defects and the unit rule | 1, 2, 3 |
| Skill catalog (`search_skills`, `install_skill`) | Search before writing a converter | 1 |
| Base skills (`aidrin`, `datacard-generator`, `skill-creator`) | Readiness metrics, the datacard, the curation skill | 1 to 5 |
| Registered codes and execution records (`save_code_spec`, `dsagt-run`) | Every conversion, cleaning, feature, and training step | 1 to 4 |
| AI-readiness check and `readiness_reports` | Baseline around every tabular stage; the readiness record | 1, 2, 3, 5 |
| Pipeline reconstruction (`reconstruct_pipeline`) | `audit/pipeline.sh` | 5 |
| Packaging a skill (`save_skill`) | `skills/battery-curation/` | 5 |
| Observability (MLflow traces, `dsagt info`, `dsagt traces`) | `audit/session_report.md` | 5 |
| Genesis datacard (`datacard-generator`, `datacard-validate`) | `data/genesis_datacard_features.md` | 5 |

## Execution

### Mission 1. From a raw file to a table

```text
The labs sent documentation with the data, in docs/. Make it searchable in this session. Then
describe the structure of data/cycles_raw.h5 and tell me whether it is ready to train a model on,
citing the documentation where it explains something in the data. Don't change anything yet.
```

```text
Before writing anything, check whether an existing skill already turns this kind of HDF5 file into
a table, and tell me what you found. If none fits, turn data/cycles_raw.h5 into one table,
data/cycles_raw.csv: one row per cycle, with cell_id, the eight per-cycle channels, and every group
attribute as columns; the discharge curves stay in the HDF5 file. Copy the values as they are: no
cleaning, no unit conversion, no attribute left out. Make the conversion a
step someone else can rerun by name, and tell me how good the table is.
```

**dsagt, unprompted:**
- ingests `docs/` with `kb_ingest`, polls `kb_job_status` until it completes, and answers from `kb_search`;
- searches the skill catalogs with `search_skills`;
- writes the converter under `skills/<name>/scripts/`, registers it, and runs it through its `dsagt-run` line;
- runs the AIDRIN quality baseline on the HDF5 file and on `data/cycles_raw.csv`.

**Expect:**
- A knowledge-base collection with the four documents; ingestion takes a minute or two on the local embedder.
- The assessment cites lab A's restarts and thermocouples, lab B's `-9999` and aborted tests, and lab C's units.
- The skill search finds nothing that flattens cycler HDF5 into a table: the `genesis` catalog's nearest matches are `data-exploration` and `well-convert`. A custom converter is the right call.
- AIDRIN refuses the HDF5 file: *"HDF5 file has 1081 datasets in an incompatible layout; refusing to flatten into one table."*
- `data/cycles_raw.csv`: 115,373 rows (lab A 83,735, B 19,669, C 11,969) and 18 columns, `lab`, `nominal_capacity`, the unit columns, and `logger_missing_value` among them. **Check the header:** a converter can keep only `cell_id` and the eight channels and report "9 columns" without flagging it; mission 2 then has no units to convert from.
- Baseline: completeness 0.9987 (`internal_resistance` 0.9797), duplicity 0.0047, outliers 0.0427 (`max_temperature` 0.120, `discharge_capacity` 0.104).

> **Hint, if the documentation was not ingested:** "Can you search the labs' documentation from here, or only read it file by file?"
>
> **Hint, if the converter fails on `discharge_curve` or writes 400 curve columns:** "Which datasets are one value per cycle, and which are not?"
>
> **Hint, if the table has no attribute columns:** "Does data/cycles_raw.csv have every group attribute as a column, as I asked?"

### Mission 2. Make it trustworthy

```text
Clean data/cycles_raw.csv into data/cycles_clean.csv so a model learns battery physics, not logger
artifacts: each (cell, cycle) once, readings the logger could not take as missing values, every
cell's values in Ah and degC as the labs' documentation says to convert them, and temperature
spikes removed without removing real degradation. Make each change its own recorded step. Tell me
your plan before proceeding.
```

```text
Go ahead.
```

**dsagt, unprompted:** searches the knowledge base for the sentinel, the units, and the spike description; registers each stage as a code; runs the AIDRIN baseline on each stage's input and output and reports the change per stage before the next one, also when the stages run from one request.

**Expect** (measured on the reference pipeline; the spike stage's values depend on the detector):

| Stage | Metric | pre | post |
|---|---|---|---|
| dedup | duplicity | 0.0047 | 0.0 (560 rows removed) |
| sentinel | completeness (`max_temperature`) | 1.0 | ≈0.991 |
| sentinel | completeness (`internal_resistance`) | ≈0.980 | ≈0.972 |
| units | outliers (`discharge_capacity`) | ≈0.104 | 0.0 |
| units | outliers (overall) | ≈0.041 | ≈0.008 |
| spikes | outliers (`max_temperature`) | ≈0.019 | ≈0.012 |

The sentinel stage lowers completeness: the raw table hid 1,000 missing temperatures and 858 missing resistances as `-9999`. Point this out if the group does not.

**Check the trap here:** in `data/cycles_clean.csv`, `nominal_capacity` must be 1.1 for every cell. Lab C's site notes say its nominal capacity is in mAh too, so an agent that searched the documentation converts it; one that read only the unit attributes does not, and mission 3's labels for lab C all come out as 1. Let it run; missions 3 and 4 are where the group finds it.

> **Hint, if a stage is missing:** "Does any -9999 survive in data/cycles_clean.csv?" An agent can plan four requirements and implement three: one run had no sentinel stage, kept all 1,000 temperature and 858 resistance `-9999` values, and did not notice from its own AIDRIN baseline.
>
> **Hint, if no readiness numbers appear per stage:** "Show me how each stage changed the table's data quality, measured before and after."

### Mission 3. A training table that is fair and safe to share

```text
Which columns of data/cycles_clean.csv carry no information, and what should I do with them?
```

```text
Build data/features.csv, one row per cell, from data/cycles_clean.csv, as a recorded step. Columns:
lab, operator, the capacity fade slope over cycles 10 to 100, the mean max_temperature and mean
internal_resistance over the first 100 cycles, the internal_resistance change over the first 100
cycles, the mean avg_voltage over the first 100 cycles, and cycle_life as the campaign protocol
defines it. Add life_class: short when cycle_life is under 550, long otherwise. Leave out cells
without a cycle life. Then tell me whether it is ready to train on, each number from a recorded
measurement: the class balance, how well each lab is represented, whether the share of short-lived
cells differs by lab, how strongly each feature relates to cycle_life, and the re-identification
risk of operator and lab. Check that cycle_life is comparable across labs, and say what must change
before the table is shared, given the campaign's data policy.
```

**dsagt, unprompted:** answers the first question with `aidrin run constant-feature-count`; takes the cycle-life definition and the data policy from `kb_search`; reaches for the `aidrin` skill's fairness and privacy metrics for the second question. The second is the likeliest place for the agent to write its own analysis instead; an agent that does can report `k = 14` (AIDRIN gives 6) and call the re-identification risk low. Ask the group whether the numbers come from a recorded run.

**Expect:**
- Constant columns: `ambient_humidity` (45.0: stuck, or the chamber's setpoint; either way no information) and `chemistry`, plus what curation made constant (the unit columns, and `nominal_capacity` when it was converted). Six in the reference pipeline.
- 114 cells; the six aborted lab B cells are left out.

| Measurement | Correct run | Trap armed (lab C labels = 1) |
|---|---|---|
| `class-imbalance` on `life_class` | ≈0.70 (97 long, 17 short) | ≈0.53 (87 long, 27 short) |
| `representation-rate` on `lab` | A:B 4.67, A:C 7.0 | same |
| `statistical-rates` of `life_class` by `lab` | about equal (TSD ≈0.01) | lab C 100 % short (TSD ≈0.40) |
| `feature-relevance` to `cycle_life` | resistance change ≈−0.79, fade slope ≈0.69, temperature ≈−0.59 | weaker (≈−0.42, 0.50, −0.39) |
| `k-anonymity` on `operator,lab` | `k = 6` | same |
| `single-attribute-risk`, `operator` | mean ≈0.85 | same |

A correct verdict: the label is imbalanced, so report error per class or range; lab C is 10 % of the cells, so check the model's error there; pooling the labs is sound; and the data policy requires `operator` to leave the table before it is shared, which the re-identification risk confirms.

> **Hint, if lab C is 100 % short and the group accepts it:** "Is it plausible that every lab C cell died at cycle 1? Compare cycle_life by lab, and check what lab C's notes say about its units."

### Mission 4. Train, and show that curation helped

```text
Train a random forest regressor on the numeric features of data/features.csv to predict
cycle_life, as a recorded step: report 5-fold cross-validated R^2 and mean absolute percentage
error, and save the model to models/cycle_life.joblib. Then compute the same features from
data/cycles_raw.csv into data/features_raw.csv, train the same model on it without saving, and
compare the two.
```

```text
If the curated model is not the better one, or a lab's cycle_life looks wrong, find the step that
caused it from the execution records, the stage files, and the labs' documentation, fix that code,
and rerun from that step to the model. Otherwise, confirm that cycle_life is comparable across labs.
```

**dsagt, unprompted:** registers the training script and runs it through `dsagt-run`, so both training runs are records with their scores in the output; reuses the registered feature code for `features_raw.csv`.

**Expect:**
- Correct run: the curated model beats the uncurated one. The reference pipeline scores R² ≈0.77 (MAPE ≈12.5 %) against ≈0.59 (MAPE ≈15.5 %); a run with correct cleaning can land lower, near 0.58 against 0.54, when it computes the resistance change from single endpoint cycles instead of averaging ten cycles at each end. To tell a feature choice from a cleaning defect, run `facilitator/scripts/reference_pipeline.py`'s `features()` on the group's `cycles_clean.csv`: correct cleaning gives ≈0.77.
- Trap armed: curated R² below zero, MAPE in the thousands of percent; the agent may recommend the uncurated data, blaming lab bias.
- A curated model that only ties the uncurated one (R² 0.56 against 0.60, say): look for a defect the cleaning left in. The usual one is the `-9999` sentinel, which drags lab B's mean temperature and resistance features far below zero; check `data/features.csv` for negative means. An agent that answers "no fix required" fails the mission.
- After the fix: the unit code converts `nominal_capacity`, the stages from it on are rerun, and the scores match the correct run. The fix is one code and a rerun, not a new session.

> **Hint:** "Which execution record first produced a lab C value you don't believe? Open that stage's output."

### Mission 5. Hand-off

```text
Use the datacard-generator skill to write a Level 1 datacard (discoverability only) for
data/features.csv that carries the readiness findings, as data/genesis_datacard_features.md. Take
the values from the data and the reports, note anything unknown rather than asking, then validate
the card with the skill's registered validator and fix what it reports.
```

```text
Generate the pipeline from data/cycles_raw.h5 to the model as a bash script from the recorded runs,
not by hand, and save it to audit/pipeline.sh.
```

```text
Show me every data-quality and readiness measurement of this session as a table of file, metric,
and value, in the order they ran.
```

```text
Package the curation as a skill named battery-curation that the labs can follow on their next
campaign's HDF5 file to get from the raw file to cycles_clean.csv. It uses the codes this session
registered, in order, with the readiness check around each stage, and says what the labs'
documentation requires (the sentinel, the units, the spikes).
```

The session report is a participant step at a terminal, not an agent prompt, because the `dsagt` CLI is for people:

```bash
dsagt info battery-life      # tokens, errors, traces by source, the knowledge base, the skills
dsagt traces battery-life    # the MLflow viewer, after collecting the last turn's trace
```

The participant then pastes the `dsagt info` output into the session and asks for `audit/session_report.md`.

**dsagt, unprompted:**
- the datacard comes from the `datacard-generator` base skill, and its validation runs as the registered `datacard-validate` code, which leaves a record;
- the script comes from `reconstruct_pipeline`;
- the readiness table comes from `readiness_reports`;
- the skill is written with the `skill-creator` base skill's guidance and saved with `save_skill`, which registers it and mirrors it into the agent's native skills.

**Expect:**
- The datacard sets `supports_discoverability` only and validates with no findings. Validating with `linkml-validate` directly leaves no record and fails the criterion; agents do this even when the prompt names the registered validator.
- `audit/pipeline.sh` lists the converter, the cleaning stages, the feature code, and the training code in run order, as the recorded commands (without the `dsagt-run` wrapper), with failed attempts as comments.
- The readiness table lists one AIDRIN report per measurement. `trace_archive/` holds more `aidrin` records than the table has rows: `--help`, `list`, `-h`, and failed calls are records without a report.
- `skills/battery-curation/SKILL.md` names the registered codes in order and appears in `dsagt info`'s skill list.
- `dsagt info` reports tokens in and out, errors, and agent turns; most input tokens are the agent's cached context. The turn a participant asked last is collected at the next session start; `dsagt traces` collects it first.

> **Hint, if the script is hand-written or the table comes from grepping files:** "Can dsagt generate that from its records?"
>
> **Debrief question for the session report:** which mission used the most tokens, and was it the one that did the most work?

## Post-Conditions

1. The converter, each cleaning stage, the feature code, and the training code are registered codes under `skills/`, each `executable` wrapped in `dsagt-run`.
2. A knowledge-base collection holds the four documents in `docs/`.
3. `data/cycles_raw.csv` (18 columns), `data/cycles_clean.csv`, `data/features.csv` (114 rows), and `data/features_raw.csv` exist.
4. `trace_archive/` holds one execution record per code run, and `aidrin` baseline records before and after each cleaning stage.
5. In `data/features.csv`, every lab's minimum `cycle_life` is above 250.
6. `models/cycle_life.joblib` exists, and the training records report a curated R² above the uncurated one.
7. `data/genesis_datacard_features.md` exists, and a `datacard-validate` record shows no findings.
8. `audit/pipeline.sh` was written by `reconstruct_pipeline`.
9. `skills/battery-curation/SKILL.md` exists.
10. MLflow traces in the project's `mlflow.db`; `dsagt info <project>` summarizes them.

## Instructor Key

The defects the generator plants, and where the documentation explains them:

| Defect | Where | What reports it | Documented in |
|---|---|---|---|
| Nested per-cell groups of different lengths | whole file | AIDRIN refuses the HDF5 file | campaign protocol (delivery format) |
| Logger restarts replayed 40 cycles | 14 lab A cells | duplicity | lab A notes |
| `-9999` written for dropped readings | lab B, temperature and resistance | outliers before decoding, completeness after | lab B manual |
| Resistance channel dropouts (NaN) | lab B | completeness | lab B manual |
| Capacity in mAh, temperature in degF | lab C, declared in attributes | outliers, skewness | lab C notes |
| Nominal capacity in mAh | lab C, an attribute that becomes a column | statistical-rates on the training table (lab C 100 % short), and the model score | lab C notes only |
| Thermocouple spikes (+35 to +60 °C) | ~1 % of lab A readings | outliers | lab A notes |
| Stuck humidity reading, single chemistry | all cells | constant-feature-count | not documented |
| Tests aborted at cycle 300, before end of life | 6 lab B cells | no label; `test_status` | lab B manual, campaign protocol |
| Lab A is 70 % of the cells; 15 % short-lived | campaign design | representation-rate, class-imbalance | not documented |
| Operator names on every cell | group attributes | single-attribute-risk | campaign protocol (data policy) |

[`../scripts/make_dataset.py`](../scripts/make_dataset.py) documents how each one is generated and holds the documents' text.
