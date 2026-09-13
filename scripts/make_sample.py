from sklearn.datasets import load_breast_cancer
import pandas as pd

data = load_breast_cancer(as_frame=True)
df = data.frame.iloc[:, :8].copy()   # keep it small and readable
df["Outcome"] = data.target
df.to_csv("samples/data.csv", index=False)
print(df.shape, list(df.columns))