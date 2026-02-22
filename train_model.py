import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier

# Load dataset
df = pd.read_csv("StudentsPerformance.csv")

# Create risk label
df["average"] = (df["math score"] + df["reading score"] + df["writing score"]) / 3

def categorize(score):
    if score < 50:
        return 0
    elif score < 75:
        return 1
    else:
        return 2

df["risk"] = df["average"].apply(categorize)

X = df[["reading score", "writing score"]]
y = df["risk"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

models = {
    "Logistic Regression": LogisticRegression(max_iter=1000),
    "Random Forest": RandomForestClassifier(),
    "Gradient Boosting": GradientBoostingClassifier()
}

results = []
best_model = None
best_accuracy = 0

for name, model in models.items():
    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    acc = accuracy_score(y_test, preds)

    results.append({
        "Model": name,
        "Accuracy": acc,
        "Precision": precision_score(y_test, preds, average="weighted"),
        "Recall": recall_score(y_test, preds, average="weighted"),
        "F1 Score": f1_score(y_test, preds, average="weighted")
    })

    if acc > best_accuracy:
        best_accuracy = acc
        best_model = model

results_df = pd.DataFrame(results)
results_df.to_csv("model_results.csv", index=False)

# Save best model
joblib.dump(best_model, "model.pkl")

print("Model Comparison Completed")
print(results_df)