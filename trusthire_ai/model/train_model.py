"""Train the optional TrustHire TF-IDF + Logistic Regression pipeline.

Use an appropriately licensed and labelled dataset, not the tiny demo examples,
for meaningful evaluation or deployment.
CSV columns: text,label; labels must be fake/genuine (or fraudulent/legitimate).
"""

import argparse
import csv
import os
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LABEL_MAP = {
    "fake": "fake", "fraudulent": "fake", "scam": "fake",
    "genuine": "genuine", "legitimate": "genuine", "real": "genuine",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_file", type=Path, help="CSV file with text,label columns")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(os.path.join(BASE_DIR, "model", "model.pkl")),
    )
    args = parser.parse_args()

    texts, labels = [], []
    with args.csv_file.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            text = (row.get("text") or "").strip()
            label = LABEL_MAP.get((row.get("label") or "").strip().lower())
            if text and label:
                texts.append(text)
                labels.append(label)
    if len(texts) < 20 or len(set(labels)) != 2 or min(labels.count("fake"), labels.count("genuine")) < 2:
        raise SystemExit("Need at least 20 labeled rows and at least 2 examples of each class.")

    x_train, x_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.2, random_state=42, stratify=labels
    )
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), max_features=80_000, min_df=1)),
        ("classifier", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)),
    ])
    pipeline.fit(x_train, y_train)
    prediction = pipeline.predict(x_test)
    print("Holdout metrics (small or non-representative datasets are not reliable):")
    print(classification_report(y_test, prediction, labels=["genuine", "fake"], zero_division=0))
    print("Confusion matrix [genuine, fake]:")
    print(confusion_matrix(y_test, prediction, labels=["genuine", "fake"]))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, args.output)
    print(f"Saved model: {args.output}")


if __name__ == "__main__":
    main()
