# Tutorial Plan: Battery Cycling, Raw Logs to a Cycle-Life Model

The facilitator's plan for running the [battery-cycling exercise](../README.md) as a hands-on session. Participants write their own prompts against five missions; the [facilitator reference](README.md) holds, per mission, a reference prompt, what dsagt should do unprompted, the hints, and the expected values.

## Purpose

Participants take a raw, defective HDF5 campaign and its lab documentation to a trained model with DSAgt and their own agent. On the way they use each part of DSAgt: the knowledge base, skills (catalog search, the base skills, and packaging their own), registered codes and execution records, the AIDRIN readiness check, observability (MLflow traces), and the Genesis datacard; the facilitator reference maps each part to its missions. They see three things a notebook does not show them:

1. **Readiness is measured, not asserted.** dsagt measures the data before and after every transformation, so each cleaning step has a number attached to it.
2. **Every step is reproducible.** The agent's scripts become registered codes, every run is an execution record, and the pipeline is generated from those records.
3. **The agent is not the authority.** The agent makes mistakes that look reasonable; the measurements and the records are how a person catches them.

The missions name outcomes, never tools. Whether the agent reaches for AIDRIN, `dsagt-run`, `reconstruct_pipeline`, and `readiness_reports` without being told is what the session shows; the hints name them only when a group is stuck.

## Audience and prerequisites

Scientists and data engineers who prepare data for machine learning. No battery background is needed. Each participant needs:

- DSAgt installed (`pip install "git+https://github.com/AI-ModCon/dsagt.git"`)
- An agent platform installed and authenticated (Claude Code, Goose, Codex, opencode, or Cline)
- Python 3.12 or later; `h5py`, `pandas`, and `scikit-learn` come with dsagt

## Agenda

| Time | Block | Participants see |
|---|---|---|
| 0:00 | Framing and setup | The task, what is real and what is made up, a running session |
| 0:15 | Mission 1. From a raw file to a table | The documentation becomes searchable; the skill search comes up empty; the check refuses the HDF5 file; the converter becomes a recorded step |
| 0:35 | Mission 2. Make it trustworthy | Each cleaning stage with its before-and-after measurement, and the documentation behind each rule |
| 0:55 | Mission 3. Training table, fair and shareable | Constant columns, class balance, lab representation, re-identification risk against the data policy |
| 1:15 | Mission 4. Train, and show that curation helped | A curated model that may lose to the raw one, and why |
| 1:30 | Mission 5. Hand-off | Datacard, generated pipeline, readiness record, a reusable skill, the session's cost from its traces |
| 1:50 | Debrief | What to take back to their own data |

A group that falls behind gets the next mission's checkpoint file.

## Before the session

- [ ] Publish this repository and have participants clone it before the session; the setup runs `scripts/make_dataset.py` from the clone.
- [ ] Dry-run the reference prompts on the agent most participants will use (command in the [facilitator reference](README.md#tools)), and keep that project to show when a group's run goes another way.
- [ ] Write the checkpoint files with `facilitator/scripts/reference_pipeline.py` and have them ready to hand out.
- [ ] Check that `python -c "import h5py, sklearn"` works in the environment dsagt is installed in; the generator runs there.
- [ ] Warm the local embedder on each machine (a throwaway `dsagt init` with a knowledge collection, or one ingest), so mission 1 does not wait on the model download.
- [ ] Tell participants to leave `facilitator/` closed: the clone includes it.

## Running each block

**Framing (15 min).** A fast-charge campaign ran 120 cells at three labs. The question is the one Severson et al. answered: can the first 100 cycles predict when a cell falls to 80 % of its capacity? The labs sent one HDF5 file and a few pages of notes; nobody has looked at either. Read the README's "What is real and what is made up" aloud: the task and the defect types are real, the data, labs, people, and documents are not, and the model says nothing about real batteries. Then setup, and the rules from "How to work": outcomes, not tools; ask why before accepting.

**During each mission,** walk the room with the facilitator reference open. Look at three things per group: whether the deliverable exists under its name, whether the step is a registered code with an execution record, and whether readiness numbers appeared. Give a hint only after a group has tried twice.

**Discussion per mission:**

1. *Raw file to table.* The raw table scores well (completeness 0.9987). Does that mean it is ready? Which defects did the documentation explain before any measurement found them? Why write a converter only after searching the skill catalogs?
2. *Trustworthy.* Why did completeness go down after the sentinel stage? Where did the capacity "outliers" go after the unit stage? Then: list every column the unit stage changed. Check `nominal_capacity` in each group's `cycles_clean.csv`; the groups where it is not 1.1 everywhere are the ones mission 3 will surprise.
3. *Training table.* Read `statistical-rates` before the agent's verdict. A constant humidity reading is a hardware fault worth reporting to the lab, not only a column to drop.
4. *Train.* For groups with the trap armed: AIDRIN reported the symptom (lab C 100 % short-lived); did the agent explain it correctly? Which record shows the cause soonest? The fix is one code and a rerun from that step: that is what registered codes and records buy. An agent's confident verdict is a hypothesis.
5. *Hand-off.* What does a reviewer need besides `audit/pipeline.sh` to reproduce the model? (The generator's seed and the code versions; both are in the records.) What does the `battery-curation` skill give the next campaign that the script does not? Which mission used the most tokens, and was it the one that did the most work?

**Debrief (10 min).** The output is a trained model, the AI-ready table it was trained on, a datacard, a generated pipeline, the readiness record from raw file to model, a skill for the next campaign, and the session's traces. Ask each participant to name one defect in their own data that a before-and-after measurement would have caught. Cleanup: `dsagt rm battery-life -y`.

## Grading

Grade artifacts, not transcripts: two groups that prompted differently can both pass. The exercise README's Review section lists the files; the facilitator reference's Post-Conditions add what to check in them (114 training rows, every lab's minimum cycle life above 250, curated R² above uncurated, a validated datacard, a generated pipeline, per-stage readiness records).
