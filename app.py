import streamlit as st
import pandas as pd
from collections import Counter
import io

# 函數：嘗試不同編碼讀取 CSV 並提供調試信息
def read_csv_with_encoding(file):
    encodings = ['utf-8', 'big5', 'gbk', 'latin1', 'iso-8859-1']
    st.write("開始嘗試讀取檔案，測試以下編碼：", encodings)
    
    for encoding in encodings:
        try:
            st.write(f"嘗試使用編碼: {encoding}")
            file.seek(0)  # 重置文件指針
            df = pd.read_csv(file, encoding=encoding)
            st.write(f"成功使用 {encoding} 讀取檔案")
            return df, encoding
        except UnicodeDecodeError as ude:
            st.write(f"編碼 {encoding} 失敗，錯誤信息: {str(ude)}")
        except Exception as e:
            st.write(f"編碼 {encoding} 發生其他錯誤: {str(e)}")
    
    # 如果所有編碼失敗，嘗試用 latin1 作為最後手段
    st.write("所有標準編碼失敗，嘗試使用 latin1 並忽略錯誤字符")
    file.seek(0)
    try:
        # 將檔案內容讀為字節，然後解碼為字符串，忽略錯誤
        content = file.read().decode('latin1', errors='replace')
        df = pd.read_csv(io.StringIO(content))
        st.write("成功使用 latin1 (忽略錯誤字符) 讀取檔案")
        return df, 'latin1 (with error replacement)'
    except Exception as e:
        st.error(f"最終嘗試失敗，無法讀取檔案: {str(e)}")
        return None, None

# 函數：計算本區和外區統計
def calculate_staff_stats(df):
    required_columns = ['RespStaff', '2ndRespStaffName', 'CaseNumber', 'NumberOfSession']
    st.write("檢查必要欄位:", required_columns)
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"缺少必要欄位: {missing_columns}")

    st.write("開始計算每位員工的本區...")
    staff_total_stats = {}
    staff_outside_stats = {}

    # 確定本區
    staff_case_counts = df.groupby('RespStaff')['CaseNumber'].value_counts().unstack(fill_value=0)
    staff_main_case = staff_case_counts.idxmax(axis=1).to_dict()
    st.write("每位員工的本區 (最高頻次 CaseNumber):", staff_main_case)

    st.write("開始遍歷數據，計算個人與協作次數...")
    for index, row in df.iterrows():
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
            if case_number != main_case:
                staff_outside_stats[resp_staff]['個人'] += 1
        else:
            staff_total_stats[resp_staff]['協作'] += 1
            if second_staff not in staff_total_stats:
                staff_total_stats[second_staff] = {'個人': 0, '協作': 0}
            staff_total_stats[second_staff]['協作'] += 1

            if case_number != main_case:
                staff_outside_stats[resp_staff]['協作'] += 1
                if second_staff not in staff_outside_stats:
                    staff_outside_stats[second_staff] = {'個人': 0, '協作': 0}
                staff_outside_stats[second_staff]['協作'] += 1

    st.write("計算完成，返回統計結果")
    return staff_total_stats, staff_outside_stats

# Streamlit 主介面
def main():
    st.title("員工活動統計工具")
    st.write("請上傳 CSV 檔案以計算員工的本區與外區統計結果。")

    # 檔案上傳功能
    uploaded_file = st.file_uploader("選擇 CSV 檔案", type=["csv"])

    if uploaded_file is not None:
        st.write("檔案已上傳，名稱:", uploaded_file.name)
        try:
            # 讀取檔案並檢測編碼
            df, used_encoding = read_csv_with_encoding(uploaded_file)
            if df is None:
                st.error("無法讀取檔案，請檢查檔案格式或內容")
                return

            st.write(f"檔案成功解析，使用編碼: {used_encoding}")
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
            st.write("請檢查檔案是否為有效的 CSV 格式，並包含必要欄位")
    else:
        st.info("請上傳一個 CSV 檔案以開始分析。")

if __name__ == "__main__":
    main()
