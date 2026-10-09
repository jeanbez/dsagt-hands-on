"""Write the battery-cycling walkthrough's raw data: one HDF5 file, one group per cell.

The data are synthetic and seeded, so every run writes the same file.  Each cell
fades along ``Q(n) = Q0 * (1 - 0.2 * (n / L) ** p)``, which reaches 80 % of its
nominal capacity at cycle ``L``, its cycle life; the early-cycle fade rate,
temperature, and resistance growth carry ``L``, so a model can learn it from the
first 100 cycles.  The file carries the defects a real multi-lab campaign
does, each one a thing AIDRIN reports once the file is a table:

- lab A loggers restarted mid-test and replayed cycles (duplicity);
- lab A thermocouples spike (outliers);
- lab B's logger writes -9999 when a channel drops, and its resistance channel
  drops out (completeness, once the sentinel is read as missing);
- lab B aborted some tests before end of life, so those cells have no label;
- lab C records capacity in mAh and temperature in degF, said only in the
  group attributes (skewness, outliers);
- the humidity sensor is stuck and the chemistry is the same everywhere
  (constant-feature-count);
- lab A supplies 70 % of the cells, and few cells are short-lived
  (representation-rate, class-imbalance);
- each cell names its operator (k-anonymity, single-attribute-risk).

It also writes the labs' documentation, the exercise's knowledge base: the
campaign protocol and one note per lab.  The documents are as made up as the
data; they explain the defects a careful reader can find in them, and lab C's
notes are the only place that says its nominal capacity is in mAh.

    python make_dataset.py <project_dir>  # writes data/cycler_raw.h5 and docs/*.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import h5py
import numpy as np

SEED = 7
LABS = {"A": 84, "B": 24, "C": 12}
OPERATORS = {
    "A": ["M. Okafor", "J. Lindqvist", "R. Tanaka", "S. Moreau"],
    "B": ["D. Alvarez", "P. Novak"],
    "C": ["K. Haddad", "L. Brennan"],
}
NOMINAL_AH = 1.1
SENTINEL = -9999.0
T0 = 1_735_689_600.0  # 2025-01-01T00:00:00Z
# Each cycle's discharge curve is sampled at these voltages; 400 points over
# about 115,000 cycles make the file about 200 MB, the curves' own stream
# leaving every other value unchanged.
VOLTAGE_GRID = np.linspace(3.6, 2.0, 400)
BANNER = (
    "> Synthetic document, written for the DSAgt battery-cycling exercise. The\n"
    "> consortium, the labs, the people, and every value are made up.\n\n"
)
DOCS = {
    "campaign_protocol.md": """# Fast-Charge Cycle-Life Campaign: Protocol

## Cells and test

All three labs test the same cell: a cylindrical LFP/graphite cell with a
nominal capacity of 1.1 Ah. Each cell is charged with a fast-charge step to
80 % state of charge, then at 1C to full, and discharged at 4C, in a chamber
held at 30 degC.

## End of life

A cell reaches end of life at the first cycle whose discharge capacity is
below 80 % of its nominal capacity; that cycle number is its cycle life. Labs
keep cycling a cell for about 10 % of its life past that point and then
stop the test. A test that stops before end of life is recorded with
`test_status = aborted`, and the cell has no cycle life.

## Data delivery

Each lab delivers one HDF5 group per cell under `/cells/<serial>`, holding one
1-D dataset per channel and attributes that describe the cell and the test.
Beside the channels, `discharge_curve` holds one row per cycle: the capacity
delivered as the voltage falls, at the voltages in the file's root
`voltage_grid` dataset, in the lab's capacity unit.
The `capacity_units`, `temperature_units`, and `resistance_units` attributes
declare the units the lab's software wrote.

## Data policy

The Fast-Charge Cycle-Life Consortium publishes the campaign's datasets.
Operator names are personal data under the consortium agreement. They stay
inside the consortium and are removed from any dataset shared outside it.
""",
    "lab_A_notes.md": """# Lab A: Site Notes

Lab A runs 84 cells on four operators' shifts.

## Logger restarts

The cyclers lost power several times during the campaign. On restart, the
logger replays the cycles held in its buffer, up to 40, before it resumes, so
an affected cell records some cycles twice with the same cycle index.

## Thermocouples

The thermocouple is taped to the cell can. When the tape loosens, the reading
jumps 35 to 60 degC above the true temperature for a single cycle and returns
when the contact settles.
""",
    "lab_B_logger_manual.md": """# Lab B: Logger Manual (excerpt)

## Missing readings

When a channel cannot take a reading, the logger writes -9999 in its place.
Each cell group declares this value in its `logger_missing_value` attribute.

## Internal resistance

Resistance is measured with a 10 ms current pulse. The pulse is skipped when
the channel is busy, and the reading is then left empty.

## Aborted tests

A channel board failed at cycle 300. The six tests on it were stopped there,
before end of life, and are recorded as aborted.
""",
    "lab_C_site_notes.md": """# Lab C: Site Notes

Lab C's cycler software exports capacity in mAh and temperature in degF.
This applies to every capacity the lab records, the nominal capacity in each
cell's attributes included: Lab C's 1100 mAh is the same 1.1 Ah cell the
other labs test. Convert before comparing Lab C's values with another lab's.
""",
}


def cell_cycles(rng: np.random.Generator, life: int, n_cycles: int) -> dict:
    """One cell's per-cycle channels, in Ah, degC, and mOhm."""
    n = np.arange(1, n_cycles + 1)
    p = rng.uniform(1.3, 1.9)
    q0 = NOMINAL_AH * rng.normal(1.0, 0.005)
    fade = 1 - 0.2 * (n / life) ** p
    discharge = q0 * fade + rng.normal(0, 0.002, n.size)
    # Short-lived cells run hot; the offset is set at the start and drifts up.
    temp = (
        30
        + 2400 / life
        + rng.normal(0, 1.5)
        + 3 * (n / life)
        + rng.normal(0, 0.4, n.size)
    )
    ir = rng.normal(18, 2.0) * (
        1 + 0.2 * (n / life) + 0.5 * (n / life) ** 2
    ) + rng.normal(0, 0.15, n.size)
    return {
        "cycle_index": n.astype(np.int32),
        "timestamp": T0 + rng.uniform(0, 30 * 86400) + n * 3.1 * 3600,
        "discharge_capacity": discharge,
        "charge_capacity": discharge * rng.normal(1.002, 0.001, n.size),
        "avg_voltage": rng.normal(3.65, 0.02)
        - 0.08 * (n / life)
        + rng.normal(0, 0.003, n.size),
        "max_temperature": temp,
        "internal_resistance": ir,
        "ambient_humidity": np.full(n.size, 45.0),
    }


def discharge_curves(
    rng: np.random.Generator, capacity: np.ndarray, aged: np.ndarray
) -> np.ndarray:
    """Capacity delivered down to each grid voltage, one row per cycle.

    The LFP plateau sits near 3.25 V and sags and widens as the cell ages
    (``aged`` is cycle / cycle life), so the curve's shape carries the fade
    the way Severson's discharge curves do.  The last point is the cycle's
    discharge capacity.
    """
    mid = 3.25 - 0.08 * aged[:, None]
    width = 0.04 + 0.03 * aged[:, None]
    shape = 1 / (1 + np.exp((VOLTAGE_GRID - mid) / width))
    shape /= shape[:, -1:]
    noise = rng.normal(0, 0.001, shape.shape)
    return ((shape + noise) * capacity[:, None]).astype(np.float32)


def build(out_dir: Path) -> Path:
    rng = np.random.default_rng(SEED)
    curve_rng = np.random.default_rng(SEED + 1)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "cycler_raw.h5"
    serial = 0
    with h5py.File(path, "w") as f:
        f.attrs["campaign"] = "Fast-charge cycle-life study, 3 labs"
        f.attrs["note"] = "Synthetic data for the DSAgt battery-cycling exercise"
        f.create_dataset("voltage_grid", data=VOLTAGE_GRID)
        f.attrs["protocol"] = "CC-CV charge 3.6C to 80% SOC, then 1C; 4C discharge"
        cells = f.create_group("cells")
        for lab, count in LABS.items():
            for k in range(count):
                serial += 1
                life = int(np.clip(rng.lognormal(np.log(850), 0.45), 250, 2300))
                n_cycles = int(life * rng.uniform(1.08, 1.15))
                censored = lab == "B" and k < 6
                if censored:
                    n_cycles = min(n_cycles, 300)
                ch = cell_cycles(rng, life, n_cycles)
                cap_units, temp_units = "Ah", "degC"

                if lab == "A" and k % 6 == 0:
                    # Logger restart: the last 40 cycles before it are replayed.
                    cut = n_cycles // 2
                    for name, arr in ch.items():
                        ch[name] = np.concatenate(
                            [arr[:cut], arr[cut - 40 : cut], arr[cut:]]
                        )
                if lab == "A":
                    spikes = rng.random(ch["max_temperature"].size) < 0.01
                    ch["max_temperature"][spikes] += rng.uniform(35, 60, spikes.sum())
                if lab == "B":
                    for name in ("max_temperature", "internal_resistance"):
                        drop = rng.random(ch[name].size) < 0.05
                        ch[name][drop] = SENTINEL
                    gaps = rng.random(ch["internal_resistance"].size) < 0.12
                    ch["internal_resistance"][gaps] = np.nan
                if lab == "C":
                    for name in ("discharge_capacity", "charge_capacity"):
                        ch[name] = ch[name] * 1000
                    ch["max_temperature"] = ch["max_temperature"] * 9 / 5 + 32
                    cap_units, temp_units = "mAh", "degF"

                g = cells.create_group(f"BC-{serial:04d}")
                g.attrs.update(
                    {
                        "lab": lab,
                        "operator": OPERATORS[lab][k % len(OPERATORS[lab])],
                        "chemistry": "LFP/graphite",
                        "nominal_capacity": NOMINAL_AH * (1000 if lab == "C" else 1),
                        "capacity_units": cap_units,
                        "temperature_units": temp_units,
                        "resistance_units": "mOhm",
                        "test_status": "aborted" if censored else "completed",
                    }
                )
                if lab == "B":
                    g.attrs["logger_missing_value"] = SENTINEL
                for name, arr in ch.items():
                    g.create_dataset(name, data=arr)
                g.create_dataset(
                    "discharge_curve",
                    data=discharge_curves(
                        curve_rng, ch["discharge_capacity"], ch["cycle_index"] / life
                    ),
                )
    return path


def demo(path: Path) -> None:
    """Every planted defect is in the file."""
    with h5py.File(path) as f:
        cells = f["cells"]
        labs = [cells[c].attrs["lab"] for c in cells]
        assert len(cells) == sum(LABS.values()) and labs.count("A") / len(labs) == 0.7
        dup = [
            c
            for c in cells
            if np.unique(cells[c]["cycle_index"][()]).size
            < cells[c]["cycle_index"].size
        ]
        assert dup and all(cells[c].attrs["lab"] == "A" for c in dup)
        b = [cells[c] for c in cells if cells[c].attrs["lab"] == "B"]
        assert any((g["max_temperature"][()] == SENTINEL).any() for g in b)
        assert any(np.isnan(g["internal_resistance"][()]).any() for g in b)
        assert sum(g.attrs["test_status"] == "aborted" for g in b) == 6
        c = [cells[c] for c in cells if cells[c].attrs["lab"] == "C"]
        assert all(g["discharge_capacity"][0] > 900 for g in c)
        assert all(g.attrs["temperature_units"] == "degF" for g in c)
        g = cells["BC-0001"]
        curve = g["discharge_curve"][()]
        assert curve.shape == (g["cycle_index"].size, VOLTAGE_GRID.size)
        assert np.allclose(curve[:, -1], g["discharge_capacity"][()], rtol=0.01)


def write_docs(docs_dir: Path) -> None:
    docs_dir.mkdir(parents=True, exist_ok=True)
    for name, text in DOCS.items():
        (docs_dir / name).write_text(BANNER + text)


if __name__ == "__main__":
    project = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    out = build(project / "data")
    demo(out)
    write_docs(project / "docs")
    print(out)
    print(project / "docs")
