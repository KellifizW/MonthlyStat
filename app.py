import streamlit as st
import pandas as pd
import requests
from io import StringIO

# GitHub Raw URL
RAW_URL = "https://raw.githubusercontent.com/KellifizW/MonthlyStat/main/homelist.csv"

# 定義預期和必要欄位
EXPECTED_COLUMNS = [
    'CaseNumber', 'RespStaffLogin', 'RespStaff', '2ndRespStaffLoginID', '2ndRespStaffName',
    'CoachedStaffLogin', 'CoachedStaff', 'Dept', 'Id', 'ServiceDate', 'ServiceTime',
    'CaseName', 'FULL_HKID', 'HomeName', 'HomeType', 'NumberOfSession', 'Remarks',
    'HomeStaffOrCarer', 'ServiceType', 'DeliveryMode', 'StartTime', 'EndTime',
    'ActualServiceMin', 'NumberOfParticipant(Without Volunteer Count)', 'NumberOfVolunteer',
    'SystolicBP', 'DiastolicBP', 'OxygenSaturation', 'PulseRate', 'BodyTemperature',
    'PostSystolicBP', 'PostDiastolicBP', 'PostOxygenSaturation', 'PostPulseRate',
    'PostBodyTemperature', 'ProgressNote', 'ServiceRemark', 'ServiceStatus',
    'LastModifiedBy', 'LastModifiedDate', 'LastModifiedTime', 'ElapseTimeBetweenService',
    'TotalService', 'TotalQualifiedSession', '活動編號', '活動名稱', '活動類型',
    '家屬所屬個案/院友編號', '家屬所屬個案/院友名稱'
]

REQUIRED_COLUMNS = ['RespStaff', '2ndRespStaffName', 'CaseNumber', 'NumberOfSession', 'ServiceDate']

# 讀取上傳的 CSV 檔案（Big5 編碼）
def read_csv_with_big5(file):
    file.seek(0)
    encoding = 'big5hkscs'
    separators = [',', '\t']
    sample = file.read(1024).decode(encoding, errors='replace')
    file.seek(0)
    separator = max(separators, key=lambda sep: sample.count(sep))

    try:
        df = pd.read_csv(file, encoding=encoding, sep=separator, on_bad_lines='warn')
        missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing_columns:
            st.error(f"CSV 文件缺少必要欄位: {missing_columns}")
            return None, None
        available_columns = [col for col in EXPECTED_COLUMNS if col in df.columns]
        df = df[available_columns]
        df['NumberOfSession'] = pd.to_numeric(df['NumberOfSession'], errors='coerce').fillna(0).astype(int)
        return df, encoding
    except Exception as e:
        st.error(f"無法讀取檔案，請檢查檔案是否為有效的 CSV: {str(e)}")
        return None, None

# 計算員工統計
def calculate_staff_stats(df):
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        st.error(f"缺少必要欄位: {missing_columns}")
        return None, None

    staff_total_stats = {}
    staff_outside_stats = {}
    staff_days = {}
    
    df['活動類型'] = df['活動類型'].fillna('未定義')
    activity_type_stats = df['活動類型'].value_counts().to_dict()

    staff_case_counts = df[df['2ndRespStaffName'].isna()].groupby('RespStaff')['CaseNumber'].value_counts().unstack(fill_value=0)
    staff_main_case = staff_case_counts.idxmax(axis=1).to_dict()

    wen_days_log = []
    xu_second_staff_log = []

    for index, row in df.iterrows():
        resp_staff = row['RespStaff']
        case_number = row['CaseNumber']
        service_date = row['ServiceDate']
        second_staff = row['2ndRespStaffName'] if pd.notna(row['2ndRespStaffName']) else None

        if pd.isna(resp_staff) or pd.isna(case_number) or pd.isna(service_date):
            continue

        if resp_staff not in staff_total_stats:
            staff_total_stats[resp_staff] = {'個人': 0, '協作': 0}
            staff_outside_stats[resp_staff] = {'個人': 0, '協作': 0}
            staff_days[resp_staff] = set()

        staff_days[resp_staff].add(service_date)
        if resp_staff == '溫?邦':
            wen_days_log.append(f"活動日期: {service_date} (作為 RespStaff, CaseNumber: {case_number})")

        main_case = staff_main_case.get(resp_staff, None)
        if main_case is None:
            continue

        is_collaboration = bool(second_staff)

        if not is_collaboration:
            if case_number == main_case:
                staff_total_stats[resp_staff]['個人'] += 1
            else:
                staff_outside_stats[resp_staff]['個人'] += 1
        else:
            if second_staff not in staff_total_stats:
                staff_total_stats[second_staff] = {'個人': 0, '協作': 0}
                staff_outside_stats[second_staff] = {'個人': 0, '協作': 0}
                staff_days[second_staff] = set()

            staff_days[second_staff].add(service_date)
            if second_staff == '溫?邦':
                wen_days_log.append(f"活動日期: {service_date} (作為 2ndRespStaffName, 與 {resp_staff}, CaseNumber: {case_number})")
            if second_staff == '徐家兒':
                xu_second_staff_log.append(f"協作記錄: {service_date}, CaseNumber: {case_number}, RespStaff: {resp_staff}")

            second_main_case = staff_main_case.get(second_staff, None)
            if case_number == main_case or (second_main_case and case_number == second_main_case):
                staff_total_stats[resp_staff]['協作'] += 1
                staff_total_stats[second_staff]['協作'] += 1
            else:
                staff_outside_stats[resp_staff]['協作'] += 1
                staff_outside_stats[second_staff]['協作'] += 1

    staff_days = {staff: len(days) for staff, days in staff_days.items()}

    combined_stats = {}
    for staff in set(staff_total_stats.keys()).union(staff_outside_stats.keys(), staff_days.keys()):
        combined_stats[staff] = {
            '本區個人 (節)': staff_total_stats.get(staff, {}).get('個人', 0),
            '本區協作 (節)': staff_total_stats.get(staff, {}).get('協作', 0),
            '外區個人 (節)': staff_outside_stats.get(staff, {}).get('個人', 0),
            '外區協作 (節)': staff_outside_stats.get(staff, {}).get('協作', 0),
            '外展日數': staff_days.get(staff, 0)
        }

    st.subheader("溫?邦 外展日數計算步驟")
    if wen_days_log:
        unique_dates = set([log.split(' ')[1] for log in wen_days_log])
        for log in wen_days_log:
            st.write(log)
        st.write(f"溫?邦 總外展日數: {len(unique_dates)} (唯一日期數: {', '.join(sorted(unique_dates))})")
    else:
        st.write("無外展日數記錄")

    st.subheader("徐家兒 作為 2ndRespStaffName 的協作記錄")
    if xu_second_staff_log:
        for log in xu_second_staff_log:
            st.write(log)
    else:
        st.write("無 2ndRespStaffName 記錄")

    return combined_stats, activity_type_stats

# 從 GitHub 讀取 homelist.csv
def get_github_csv_data(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = StringIO(response.text)
            df = pd.read_csv(data)
            return df
        else:
            st.error(f"無法獲取 GitHub CSV 檔案，狀態碼：{response.status_code}")
            return None
    except Exception as e:
        st.error(f"讀取 GitHub CSV 時發生錯誤：{str(e)}")
        return None

# 統計頁面
def stats_page():
    st.title("員工活動統計工具")
    st.write("請上傳 CSV 檔案以計算員工的本區與外區統計結果（使用 Big5HKSCS 編碼）。")
    uploaded_file = st.file_uploader("選擇 CSV 檔案", type=["csv"])

    if uploaded_file is not None:
        st.write("檔案已上傳，名稱:", uploaded_file.name)
        df, used_encoding = read_csv_with_big5(uploaded_file)
        if df is None:
            return

        st.write(f"檔案成功解析，使用編碼: {used_encoding}")
        st.write("以下是前幾行數據：")
        st.dataframe(df.head())

        combined_stats, activity_type_stats = calculate_staff_stats(df)
        if combined_stats is None:
            st.error("統計計算失敗，請檢查錯誤訊息")
            return

        st.subheader("員工活動統計總表")
        combined_df = pd.DataFrame(combined_stats).T
        combined_df = combined_df[['本區個人 (節)', '本區協作 (節)', '外區個人 (節)', '外區協作 (節)', '外展日數']]
        st.table(combined_df)

        st.subheader("活動類型統計")
        activity_df = pd.DataFrame.from_dict(activity_type_stats, orient='index', columns=['次數'])
        st.table(activity_df)

# 列表頁面
def list_page():
    st.title("GitHub homelist.csv 列表")
    st.write("從 GitHub 儲存庫讀取並顯示 homelist.csv 的內容。")

    df = get_github_csv_data(RAW_URL)
    if df is not None:
        st.subheader("homelist.csv 內容")
        st.dataframe(df)  # 顯示完整表格

        st.write("列表詳情：")
        for index, row in df.iterrows():
            st.write(f"第 {index + 1} 行：{row.to_dict()}")

# 主程式：頁面切換
def main():
    st.sidebar.title("頁面導航")
    page = st.sidebar.selectbox("選擇頁面", ["統計頁", "列表頁"])

    if page == "統計頁":
        stats_page()
    elif page == "列表頁":
        list_page()

if __name__ == "__main__":
    main()
