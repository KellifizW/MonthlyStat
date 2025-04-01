import streamlit as st
import pandas as pd
from collections import Counter

# 函數：嘗試不同編碼讀取 CSV
def read_csv_with_encoding(file):
    encodings = ['utf-8', 'big5', 'gbk', 'latin1', 'iso-8859-1']  # 常見編碼列表
    for encoding in encodings:
        try:
            df = pd.read_csv(file, encoding=encoding)
            file.seek(0)  # 重置文件指針，以便下次讀取
            return df, encoding
        except (UnicodeDecodeError, ValueError):
            continue
    # 如果所有編碼都失敗，使用 'latin1' 並忽略錯誤
    file.seek(0)
    df = pd.read_csv(file, encoding='latin1', errors='replace')
    return df, 'latin1 (with error replacement)'

# 函數：計算本區和外區統計
def calculate_staff_stats(df):
    required_columns = ['RespStaff', '2ndRespStaffName', 'CaseNumber', 'NumberOfSession']
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"缺少必要的欄位: {col}")

    staff_total_stats = {}
    staff_outside_stats = {}

    staff_case_counts = df.groupby('RespStaff')['CaseNumber'].value_counts().unstack(fill_value=0)
    staff_main_case = staff_case_counts.idxmax(axis=1).to_dict()

    for _, row in df.iterrows():
        resp_staff = row['RespStaff']
        second_staff = row['2ndRespStaffName'] if pd.notna(row['2ndRespStaffName']) else None
        case_number = row['CaseNumber']

        if resp_staff not in staff_total_stats:
            staff_total_stats[resp_staff] = {'個人': 0, '協作': 0}
            staff_outside_stats[resp_staff] = {'個人': 0, '協作': 0}

        is_collaboration = bool(second_staff)
        main_case = staff_main_case.get(resp_staff)

        if not is_collaboration:
            staff_total_stats[resp_staff]['個人'] += 1
        else:
            staff_total_stats[resp_staff]['協作'] += 1
            if second_staff not in staff_total_stats:
                staff_total_stats[second_staff] = {'個人': 0, '協作': 0}
            staff_total_stats[second_staff]['協作'] += 1

        if case_number != main_case:
            if not is_collaboration:
                staff_outside_stats[resp_staff]['個人'] += 1
            else:
                staff_outside_stats[resp_staff]['協作'] += 1
                if second_staff not in staff_outside_stats:
                    staff_outside_stats[second_staff] = {'個人': 0, '協作': 0}
                staff_outside_stats[second_staff]['協作'] += 1

    return staff_total_stats, staff_outside_stats

# Streamlit 主介面
def main():
    st.title("員工活動統計工具")
    st.write("請上傳 CSV 檔案以計算員工的本區與外區統計結果。")

    # 檔案上傳功能
    uploaded_file = st.file_uploader("選擇 CSV 檔案", type=["csv"])

    if uploaded_file is not None:
        try:
            # 讀取檔案並檢測編碼
            df, used_encoding = read_csv_with_encoding(uploaded_file)
            st.write(f"檔案已成功上傳，使用編碼：{used_encoding}")
            st.write("以下是前幾行數據：")
            st.dataframe(df.head())

            # 計算統計結果
            staff_total_stats, staff_outside_stats = calculate_staff_stats(df)

            # 顯示本區統計
            st.subheader("本區統計（總個人與協作次數）")
            total_stats_df = pd.DataFrame(staff_total_stats).T
            total_stats_df.columns = ['個人 (節)', '協作 (節)']
            st.table(total_stats_df)

            # 顯示外區統計
            st.subheader("外區統計")
            outside_stats_df = pd.DataFrame(staff_outside_stats).T
            outside_stats_df.columns = ['個人 (節)', '協作 (節)']
            st.table(outside_stats_df)

        except ValueError as ve:
            st.error(f"錯誤: {str(ve)}")
        except Exception as e:
            st.error(f"發生錯誤: {str(e)}")
    else:
        st.info("請上傳一個 CSV 檔案以開始分析。")

if __name__ == "__main__":
    main()
