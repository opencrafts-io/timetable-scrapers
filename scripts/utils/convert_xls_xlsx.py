import pandas as pd
import sys
from pathlib import Path


def convert_xls_to_xlsx(xls_file):
    xls_path = Path(xls_file)

    if not xls_path.exists():
        print(f"File not found: {xls_file}")
        return

    xlsx_file = xls_path.with_suffix(".xlsx")

    # Read old .xls file
    df = pd.read_excel(xls_file, engine="xlrd")

    # Save as .xlsx
    df.to_excel(xlsx_file, index=False, engine="openpyxl")

    print(f"Converted: {xls_file} -> {xlsx_file}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python convert.py file.xls")
    else:
        convert_xls_to_xlsx(sys.argv[1])
