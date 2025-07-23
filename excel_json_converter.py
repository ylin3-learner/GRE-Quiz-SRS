import pandas as pd
import os
import sys

def excel_to_json(input_file):
    xls = pd.ExcelFile(input_file)
    df = xls.parse(xls.sheet_names[0])  # 使用第一個工作表
    output_file = os.path.splitext(input_file)[0] + ".json"
    df.to_json(output_file, orient="records", force_ascii=False, indent=2)
    print(f"✅ Excel 轉 JSON 成功：{output_file}")

def json_to_excel(input_file):
    df = pd.read_json(input_file)
    output_file = os.path.splitext(input_file)[0] + ".xlsx"
    df.to_excel(output_file, index=False)
    print(f"✅ JSON 轉 Excel 成功：{output_file}")

def main():
    if len(sys.argv) < 2:
        print("❗請提供檔案路徑，例如：python excel_json_converter.py data.xlsx")
        return

    input_file = sys.argv[1]
    if not os.path.exists(input_file):
        print(f"❗找不到檔案：{input_file}")
        return

    ext = os.path.splitext(input_file)[1].lower()
    if ext == ".xlsx":
        excel_to_json(input_file)
    elif ext == ".json":
        json_to_excel(input_file)
    else:
        print("❗不支援的副檔名，只接受 .xlsx 或 .json")

if __name__ == "__main__":
    main()

    # python excel_json_converter.py voc_merged_fixed.xlsx
    # python excel_json_converter.py voc_merged_fixed.json

