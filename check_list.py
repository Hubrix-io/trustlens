import pandas as pd

df = pd.read_excel("data/rbi_dla_list.xlsx")

print("Rows:", len(df))
print("Columns:", list(df.columns))
print(df.head(5).to_string())