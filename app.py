import streamlit as st
import pandas as pd
import requests
from io import StringIO
import re

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

REQUIRED_COLUMNS = ['RespStaff', '2ndRespStaffName', 'HomeName', 'ServiceDate']

# 讀取 CSV 檔案（Big5HKSCS 編碼）
def read_csv_with_big5(file):
    file.seek(0)
    encoding = 'big5hkscs'
    separators = [',', '\t']
    sample = file.read(1024).decode(encoding, errors='replace')
    file.seek(0)
    separator = max(separators, key=lambda sep: sample.count(sep))

    try:
        df = pd.read_csv(file, encoding=encoding, sep=separator, on_bad_lines='warn')
        return df, encoding
    except Exception as e:
        st.error(f"無法讀取檔案，請檢查檔案是否為有效的 CSV: {str(e)}")
        return None, None

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

# 提取 HomeName 的前 1-3 個數字
def extract_home_number(home_name):
    if pd.isna(home_name):
        return None
    match = re.match(r'^\d{1,3}', str(home_name))
    return match.group(0) if match else None

# 判斷是否本區
def check_local(row, github_df):
    home_number = extract_home_number(row['HomeName'])
    resp_staff = row['RespStaff'] if pd.notna(row['RespStaff']) else None
    second_staff = row['2ndRespStaffName'] if pd.notna(row['2ndRespStaffName']) else None

    if home_number is None:
        return '外區'

    matching_homes = github_df[github_df['Home'].astype(str) == str(home_number)]
    if matching_homes.empty:
        return '外區'

    local_staff = set()
    for _, home_row in matching_homes.iterrows():
        if pd.notna(home_row['staff1']):
            local_staff.add(home_row['staff1'])
        if pd.notna(home_row['staff2']):
            local_staff.add(home_row['staff2'])

    if (resp_staff in local_staff) or (second_staff in local_staff):
        return '本區'
    return '外區'

# 計算員工統計（基於測試頁邏輯）
def calculate_staff_stats(df, github_df):
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        st.error(f"缺少必要欄位: {missing_columns}")
        return None

    staff_stats = {}

    for index, row in df.iterrows():
        resp_staff = row['RespStaff']
        second_staff = row['2ndRespStaffName'] if pd.notna(row['2ndRespStaffName']) else None
        service_date = row['ServiceDate']

        if pd.isna(resp_staff) or pd.isna(service_date):
            continue

        # 初始化員工統計
        if resp_staff not in staff_stats:
            staff_stats[resp_staff] = {
                '本區單獨': 0, '本區協作': 0, '外區單獨': 0, '外區協作': 0
            }
        if second_staff and second_staff not in staff_stats:
            staff_stats[second_staff] = {
                '本區單獨': 0, '本區協作': 0, '外區單獨': 0, '外區協作': 0
            }

        # 判斷區域
        region = check_local(row, github_df)
        is_collaboration = bool(second_staff)

        # 根據單獨或協作更新統計
        if not is_collaboration:
            if region == '本區':
                staff_stats[resp_staff]['本區單獨'] += 1
            else:
                staff_stats[resp_staff]['外區單獨'] += 1
        else:
            if region == '本區':
                staff_stats[resp_staff]['本區協作'] += 1
                staff_stats[second_staff]['本區協作'] += 1
            else:
                staff_stats[resp_staff]['外區協作'] += 1
                staff_stats[second_staff]['外區協作'] += 1

    return staff_stats

# 統計頁
def stats_page():
    st.title("員工活動統計工具")
    st.write("請上傳 CSV 檔案以計算員工的本區與外區統計結果（使用 Big5HKSCS 編碼）。")
    uploaded_file = st.file_uploader("選擇 CSV 檔案", type=["csv"], key="stats_uploader")

    if uploaded_file is not None:
        st.write("檔案已上傳，名稱:", uploaded_file.name)
        df, used_encoding = read_csv_with_big5(uploaded_file)
        if df is None:
            return

        st.write(f"檔案成功解析，使用編碼: {used_encoding}")
        st.write("以下是前幾行數據：")
        st.dataframe(df.head())

        # 讀取 GitHub 的 homelist.csv
        github_df = get_github_csv_data(RAW_URL)
        if github_df is None:
            return

        staff_stats = calculate_staff_stats(df, github_df)
        if staff_stats is None:
            st.error("統計計算失敗，請檢查錯誤訊息")
            return

        st.subheader("員工活動統計總表")
        stats_df = pd.DataFrame(staff_stats).T
        stats_df = stats_df[['本區單獨', '本區協作', '外區單獨', '外區協作']]
        st.table(stats_df)

# 列表頁
def list_page():
    st.title("GitHub homelist.csv 列表")
    st.write("從 GitHub 儲存庫讀取並顯示 homelist.csv 的內容。")

    df = get_github_csv_data(RAW_URL)
    if df is not None:
        st.subheader("homelist.csv 內容")
        st.dataframe(df)

        st.write("列表詳情：")
        for index, row in df.iterrows():
            st.write(f"第 {index + 1} 行：{row.to_dict()}")

# 測試頁
def test_page():
    st.title("測試頁：本區/外區判斷")
    st.write("請上傳 CSV 檔案，程式將根據 GitHub 的 homelist.csv 判斷每筆資料是否屬於本區（使用 Big5HKSCS 編碼）。")
    uploaded_file = st.file_uploader("選擇 CSV 檔案", type=["csv"], key="test_uploader")

    if uploaded_file is not None:
        st.write("檔案已上傳，名稱:", uploaded_file.name)
        uploaded_df, used_encoding = read_csv_with_big5(uploaded_file)
        if uploaded_df is None:
            return

        st.write(f"檔案成功解析，使用編碼: {used_encoding}")
        st.write("上傳檔案的前幾行數據：")
        st.dataframe(uploaded_df.head())

        github_df = get_github_csv_data(RAW_URL)
        if github_df is None:
            return

        required_uploaded_cols = ['HomeName', 'RespStaff', '2ndRespStaffName']
        required_github_cols = ['Home', 'staff1', 'staff2']
        missing_uploaded = [col for col in required_uploaded_cols if col not in uploaded_df.columns]
        missing_github = [col for col in required_github_cols if col not in github_df.columns]

        if missing_uploaded:
            st.error(f"上傳的 CSV 缺少必要欄位: {missing_uploaded}")
            return
        if missing_github:
            st.error(f"GitHub 的 homelist.csv 缺少必要欄位: {missing_github}")
            return

        uploaded_df['區域'] = uploaded_df.apply(lambda row: check_local(row, github_df), axis=1)

        st.subheader("判斷結果")
        st.dataframe(uploaded_df)

        region_counts = uploaded_df['區域'].value_counts()
        st.subheader("區域統計")
        st.write(f"本區記錄數: {region_counts.get('本區', 0)}")
        st.write(f"外區記錄數: {region_counts.get('外區', 0)}")

# 主程式：頁面切換
def main():
    st.sidebar.title("頁面導航")
    page = st.sidebar.selectbox("選擇頁面", ["統計頁", "列表頁", "測試頁"])

    if page == "統計頁":
        stats_page()
    elif page == "列表頁":
        list_page()
    elif page == "測試頁":
        test_page()

if __name__ == "__main__":
    main()
