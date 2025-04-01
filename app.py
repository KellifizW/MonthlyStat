import streamlit as st
import pandas as pd
from collections import Counter
import io

# 預定義的欄位名稱
EXPECTED_COLUMNS = [
    'CaseNumber', 'RespStaffLogin', 'RespStaff', '2ndRespStaffLoginID', '2ndRespStaffName',
    'CoachedStaffLogin', 'CoachedStaff', 'Dept', 'Id', 'ServiceDate', 'ServiceTime',
    'CaseName', 'HomeName', 'NumberOfSession', 'NumberOfParticipant(Without Volunteer Count)',
    '活動編號', '活動類型'
]

# 函數：自動檢測分隔符並使用 Big5 編碼讀取 CSV
def read_csv_with_big5(file):
    st.write("開始讀取 Big5 編碼的 CSV 檔案...")
    file.seek(0)
    
    # 讀取檔案開頭以檢測分隔符
    sample = file.read(1024).decode('big5', errors='replace')  # 讀取前 1024 字節
    file.seek(0)
    
    # 檢測分隔符：逗號或制表符
    if ',' in sample and sample.count(',') > sample.count('\t'):
        separator = ','
        st.write("檢測到分隔符：逗號 (',')")
    else:
        separator = '\t'
        st.write("檢測到分隔符：制表符 ('\\t')")

    try:
        # 嘗試標準 Big5 編碼
        df = pd.read_csv(file, encoding='big5', sep=separator)
        st.write(f"成功使用標準 Big5 編碼讀取檔案（分隔符：{separator}）")
        st.write(f"解析出的欄位數量: {len(df.columns)}，預期欄位數量: {len(EXPECTED_COLUMNS)}")
        if len(df.columns) != len(EXPECTED_COLUMNS):
            st.write("欄位數量不匹配，設置預定義欄位名稱")
            file.seek(0)
            df = pd.read_csv(file, encoding='big5', sep=separator, names=EXPECTED_COLUMNS, header=0)
        return df, 'big5'
    except UnicodeDecodeError:
        file.seek(0)
        content = file.read().decode('big5', errors='replace')
        df = pd.read_csv(io.StringIO(content), sep=separator, names=EXPECTED_COLUMNS, header=0)
        st.write(f"成功使用 Big5 編碼（忽略無效字符）讀取檔案（分隔符：{separator}）")
        return df, 'big5 (with error replacement)'
    except Exception as e:
        st.error(f"無法讀取檔案: {str(e)}")
        file.seek(0)
        st.write("檔案前 500 字符（調試用）：", file.read()[:500].decode('big5', errors='replace'))
        return None, None

# 函數：計算本區和外區統計
def calculate_staff_stats(df):
    required_columns = ['RespStaff', '2ndRespStaffName', 'CaseNumber', 'NumberOfSession']
    st.write("檔案實際欄位名稱:", list(df.columns))
    st.write("程式預期的必要欄位:", required_columns)
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"缺少必要欄位: {missing_columns}")

    st.write("開始計算每位員工的本區...")
    staff_total_stats = {}
    staff_outside_stats = {}

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
    st.title("員工活動統計工具 (Big5 編碼，支援逗號與制表符)")
    st.write("請上傳使用 Big5 編碼的 CSV 檔案（支援逗號或制表符分隔）以計算員工的本區與外區統計結果。")

    uploaded_file = st.file_uploader("選擇 CSV 檔案", type=["csv"])

    if uploaded_file is not None:
        st.write("檔案已上傳，名稱:", uploaded_file.name)
        try:
            df, used_encoding = read_csv_with_big5(uploaded_file)
            if df is None:
                st.error("無法讀取檔案，請檢查檔案是否為有效的 Big5 編碼 CSV")
                return

            st.write(f"檔案成功解析，使用編碼: {used_encoding}")
            st.write("以下是前幾行數據：")
            st.dataframe(df.head())

            staff_total_stats, staff_outside_stats = calculate_staff_stats(df)

            st.subheader("本區統計（總個人與協作次數）")
            total_stats_df = pd.DataFrame(staff_total_stats).T
            total_stats_df.columns = ['個人 (節)', '協作 (節)']
            st.table(total_stats_df)

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
