"""The battery-cycling exercise's reference pipeline: checkpoint files and reference values.

A facilitator runs it to hand a group that fell behind the file the next
mission starts from, and to reproduce the reference values the facilitator
notes quote.  It writes, under ``<data_dir>``:

- ``cycles_raw.csv``     mission 1's table: one row per cycle, values unchanged
- ``cycles_clean.csv``   mission 2's table: deduplicated, sentinels missing,
                         Ah and degC everywhere (``nominal_capacity`` too),
                         temperature spikes dropped
- ``features.csv``       mission 3's training table
- ``features_raw.csv``   the same features from the uncurated table

and prints the 5-fold cross-validated scores of mission 4's model on both.

    python reference_pipeline.py <data_dir>   # reads <data_dir>/cycler_raw.h5
"""

from __future__ import annotations

import sys
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import cross_val_score

FEATURES = [
    "fade_slope_10_100",
    "temp_mean_100",
    "ir_mean_100",
    "ir_delta_100",
    "voltage_mean_100",
]


def flatten(h5_path: Path) -> pd.DataFrame:
    frames = []
    with h5py.File(h5_path) as f:
        for cell_id, g in f["cells"].items():
            # The discharge curves (2-D) stay in the HDF5 file.
            df = pd.DataFrame({n: g[n][()] for n in g if g[n].ndim == 1})
            df.insert(0, "cell_id", cell_id)
            for key, value in g.attrs.items():
                df[key] = value
            frames.append(df)
    return pd.concat(frames, ignore_index=True)


def curate(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.drop_duplicates(subset=["cell_id", "cycle_index"]).copy()
    sentinel = df["logger_missing_value"].notna()
    for col in ("max_temperature", "internal_resistance"):
        df.loc[sentinel & (df[col] == df["logger_missing_value"]), col] = np.nan
    mah = df["capacity_units"] == "mAh"
    for col in ("discharge_capacity", "charge_capacity", "nominal_capacity"):
        df.loc[mah, col] = df.loc[mah, col] / 1000
    degf = df["temperature_units"] == "degF"
    df.loc[degf, "max_temperature"] = (df.loc[degf, "max_temperature"] - 32) * 5 / 9
    df["capacity_units"], df["temperature_units"] = "Ah", "degC"
    # A spike is a reading more than 10 degC off the cell's 11-cycle rolling median.
    trend = df.groupby("cell_id")["max_temperature"].transform(
        lambda t: t.rolling(11, center=True, min_periods=1).median()
    )
    return df[~((df["max_temperature"] - trend).abs() > 10)]


def features(cycles: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for cell_id, g in cycles.sort_values("cycle_index").groupby("cell_id"):
        if g["test_status"].iloc[0] != "completed":
            continue
        below = g.loc[
            g["discharge_capacity"] < 0.8 * g["nominal_capacity"], "cycle_index"
        ]
        early = g[g["cycle_index"] <= 100]
        fade = early[early["cycle_index"] >= 10]
        ir = early["internal_resistance"]
        rows.append(
            {
                "cell_id": cell_id,
                "lab": g["lab"].iloc[0],
                "operator": g["operator"].iloc[0],
                "fade_slope_10_100": np.polyfit(
                    fade["cycle_index"], fade["discharge_capacity"], 1
                )[0],
                "temp_mean_100": early["max_temperature"].mean(),
                "ir_mean_100": ir.mean(),
                "ir_delta_100": ir.iloc[-10:].mean() - ir.iloc[:10].mean(),
                "voltage_mean_100": early["avg_voltage"].mean(),
                "cycle_life": below.iloc[0] if len(below) else np.nan,
            }
        )
    out = pd.DataFrame(rows)
    out["life_class"] = np.where(out["cycle_life"] < 550, "short", "long")
    return out


def cv_scores(table: pd.DataFrame) -> tuple[float, float]:
    table = table.dropna(subset=FEATURES + ["cycle_life"])
    model = RandomForestRegressor(n_estimators=300, random_state=0)
    x, y = table[FEATURES], table["cycle_life"]
    r2 = cross_val_score(model, x, y, cv=5, scoring="r2").mean()
    mape = -cross_val_score(
        model, x, y, cv=5, scoring="neg_mean_absolute_percentage_error"
    ).mean()
    return r2, mape


def main(data_dir: Path) -> None:
    raw = flatten(data_dir / "cycler_raw.h5")
    clean = curate(raw)
    feats, feats_raw = features(clean), features(raw)
    raw.to_csv(data_dir / "cycles_raw.csv", index=False)
    clean.to_csv(data_dir / "cycles_clean.csv", index=False)
    feats.to_csv(data_dir / "features.csv", index=False)
    feats_raw.to_csv(data_dir / "features_raw.csv", index=False)

    # The generator's seed fixes these; a change means the data changed.
    assert len(raw) == 115_373 and len(feats) == 114
    assert feats.groupby("lab")["cycle_life"].min().min() > 250
    for name, table in (("curated", feats), ("uncurated", feats_raw)):
        r2, mape = cv_scores(table)
        print(f"{name:>9}: R2 {r2:.2f}  MAPE {mape:.1%}")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "data"))
