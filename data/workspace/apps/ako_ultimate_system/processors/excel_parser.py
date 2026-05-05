import pandas as pd

def parse_excel(path):
    df = pd.read_excel(path)
    return {"columns": list(df.columns), "shape": df.shape, "describe": df.describe(include="all").to_string()}
