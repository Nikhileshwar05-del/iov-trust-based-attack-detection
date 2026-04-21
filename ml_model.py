import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import ast
import re
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, label_binarize
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report, roc_curve, auc
from sklearn.ensemble import RandomForestClassifier


def run_ml():

    print("ML started...")

    # ---------------- LOAD ----------------
    df = pd.read_csv("blockchain1_log.csv")

    # ---------------- SAFE PARSE ----------------
    def safe_parse(x):
        if pd.isna(x):
            return {}
        x = re.sub(r'\bnan\b', 'None', x)
        return ast.literal_eval(x)

    df["vehicle_data"] = df["vehicle_data"].apply(safe_parse)

    # ---------------- FLATTEN ----------------
    vehicle_df = pd.json_normalize(df["vehicle_data"])
    df = pd.concat([df, vehicle_df], axis=1)

    # ---------------- CLEAN ----------------
    valid_classes = ["Normal", "Suspicious", "Critical", "Malicious"]
    df = df[df["behavior"].isin(valid_classes)]

    # ---------------- CLASS DISTRIBUTION GRAPH ----------------
    df["behavior"].value_counts().plot(kind="bar")
    plt.title("Class Distribution")
    plt.xlabel("Behavior")
    plt.ylabel("Count")
    plt.show()

    # ---------------- FEATURES ----------------
    features = [
        "msgRate",
        "delay",
        "drop",
        "fmr",
        "speed",
        "accel",
        "neighbors",
        "distance"
    ]

    X = df[features]

    # ---------------- TARGET ----------------
    mapping = {
        "Normal": 0,
        "Suspicious": 1,
        "Critical": 2,
        "Malicious": 3
    }

    y = df["behavior"].map(mapping)

    print("Class Mapping:", mapping)

    # ---------------- SPLIT ----------------
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )

    # ---------------- SCALING ----------------
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    # ---------------- MODEL ----------------
    model = RandomForestClassifier(
        n_estimators=400,
        max_depth=40,
        min_samples_split=5,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    )

    model.fit(X_train, y_train)

    # ---------------- PREDICT ----------------
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)

    # ---------------- EVALUATION ----------------
    acc = accuracy_score(y_test, y_pred)

    print("\n📊 Results")
    print("Accuracy:", round(acc, 3))

    labels = ["Normal", "Suspicious", "Critical", "Malicious"]

    print("\n📊 Classification Report:")
    print(classification_report(y_test, y_pred, target_names=labels))

    # ---------------- CONFUSION MATRIX ----------------
    cm = confusion_matrix(y_test, y_pred)

    plt.figure()
    sns.heatmap(cm, annot=True,
                xticklabels=labels,
                yticklabels=labels)
    plt.title("Confusion Matrix")
    plt.xlabel("Predicted")
    plt.ylabel("Actual")
    plt.show()

    # ---------------- PRECISION / RECALL / F1 GRAPH ----------------
    report = classification_report(y_test, y_pred, target_names=labels, output_dict=True)
    report_df = pd.DataFrame(report).iloc[:-1, :].T

    report_df[["precision", "recall", "f1-score"]].plot(kind="bar")
    plt.title("Precision, Recall, F1 Score per Class")
    plt.ylabel("Score")
    plt.xticks(rotation=0)
    plt.show()

    # ---------------- FEATURE IMPORTANCE ----------------
    importance = model.feature_importances_

    plt.figure()
    plt.barh(features, importance)
    plt.title("Feature Importance")
    plt.xlabel("Importance Score")
    plt.show()

    # ---------------- ROC CURVE ----------------
    y_test_bin = label_binarize(y_test, classes=[0, 1, 2, 3])

    plt.figure()
    for i in range(4):
        fpr, tpr, _ = roc_curve(y_test_bin[:, i], y_prob[:, i])
        plt.plot(fpr, tpr, label=labels[i])

    plt.title("ROC Curve")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.legend()
    plt.show()


# ---------------- RUN ----------------
if __name__ == "__main__":
    run_ml()