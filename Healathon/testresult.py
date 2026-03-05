from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier

# 1. Generate Synthetic Data for the Demo
np.random.seed(42)
data_size = 500
# Features: Stock (0-50), Rain (0-1), Accidents (0-1)
X = np.random.rand(data_size, 3)
X[:, 0] *= 50 # Scale stock to 50 units

# Target: If stock < 10 AND (Rain > 0.5 OR Accidents > 0.5), it's a Shortage (1)
y = ((X[:, 0] < 12) & ((X[:, 1] > 0.5) | (X[:, 2] > 0.5))).astype(int)

# 2. Split and Train
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
clf = RandomForestClassifier(n_estimators=100)
clf.fit(X_train, y_train)

# 3. Predict and Report
y_pred = clf.predict(X_test)
print("--- BLOOD-LINK MODEL VALIDATION ---")
print(f"Final Accuracy: {accuracy_score(y_test, y_pred) * 100:.2f}%")
print("\nDetailed Performance Report:")
print(classification_report(y_test, y_pred))