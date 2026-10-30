"""Clean, de-duplicate, write the train/test split."""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    df = pd.read_parquet(ROOT / "data/raw/data.parquet").dropna()
    df["text"] = df["text"].str.strip()
    df = df[df["text"] != ""].rename(columns={"intent": "target"})
    df = df.drop_duplicates(subset=["text", "split"])

    test = df[df["split"] == "test"]
    # drop train queries that also appear in test, otherwise they leak
    train = df[(df["split"] == "train") & ~df["text"].isin(test["text"])]

    out = ROOT / "data/processed"
    out.mkdir(parents=True, exist_ok=True)
    train[["text", "target"]].to_csv(out / "train.csv", index=False)
    test[["text", "target"]].to_csv(out / "test.csv", index=False)
    print(f"train={len(train)} test={len(test)} intents={df['target'].nunique()}")


if __name__ == "__main__":
    main()
