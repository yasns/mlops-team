"""Download the raw dataset once at a fixed revision."""

from pathlib import Path

import pandas as pd
import yaml
from datasets import load_dataset

p = yaml.safe_load(Path("params.yaml").read_text())["data"]

out = Path("data/raw/data.parquet")
out.parent.mkdir(parents=True, exist_ok=True)
ds = load_dataset(p["dataset"], revision=p["revision"])
df = pd.concat(ds[s].to_pandas().assign(split=s) for s in ("train", "test"))
df["intent"] = df["label"].map(ds["train"].features["label"].int2str)
df.drop(columns="label").to_parquet(out, index=False)
print(f"saved {len(df)} rows -> {out}")
