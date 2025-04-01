import streamlit as st
import pandas as pd
import io

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
        # 去重數據，避免重複計數
        df = df.drop_duplicates(subset=['RespStaff', '2ndRespStaffName', 'CaseNumber', 'ServiceDate'])
        return df, encoding
    except Exception as e:
        st.error(f"無法讀取檔案，請檢查檔案是否為有效的 CSV: {str(e)}")
        return None, None

def calculate_staff_stats(df):
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        st.error(f"缺少必要欄位: {missing_columns}")
        return None, None, None, None

    staff_total_stats = {}
    staff_outside_stats = {}
    staff_days = {}
    
    df['活動類型'] = df['活動類型'].fillna('未定義')
    activity_type_stats = df['活動類型'].value_counts().to_dict()

    # 確定每個員工的主要 CaseNumber（僅基於個人活動）
    staff_case_counts = df[df['2ndRespStaffName'].isna()].groupby('RespStaff')['CaseNumber'].value_counts().unstack(fill_value=0)
    staff_main_case = staff_case_counts.idxmax(axis=1).to_dict()

    # 記錄溫?邦的計算步驟
    wen_collaboration_log = []
    wen_days_log = []

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
            wen_days_log.append(f"個人活動日期: {service_date}")

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
                wen_days_log.append(f"協作活動日期: {service_date} (與 {resp_staff} 在 {case_number})")

            # 修正協作邏輯：僅當 case_number 等於該員工的主案件時計為本區
            if case_number == main_case:
                staff_total_stats[resp_staff]['協作'] += 1
                if resp_staff == '溫?邦':
                    wen_collaboration_log.append(f"本區協作: {service_date}, CaseNumber: {case_number}, 與 {second_staff} (主要案件: {main_case})")
            else:
                staff_outside_stats[resp_staff]['協作'] += 1
                if resp_staff == '溫?邦':
                    wen_collaboration_log.append(f"外區協作: {service_date}, CaseNumber: {case_number}, 與 {second_staff} (主要案件: {main_case})")

            second_main_case = staff_main_case.get(second_staff, None)
            if second_main_case and case_number == second_main_case:
                staff_total_stats[second_staff]['協作'] += 1
                if second_staff == '溫?邦':
                    wen_collaboration_log.append(f"本區協作: {service_date}, CaseNumber: {case_number}, 與 {resp_staff} (主要案件: {second_main_case})")
            else:
                staff_outside_stats[second_staff]['協作'] += 1
                if second_staff == '溫?邦':
                    wen_collaboration_log.append(f"外區協作: {service_date}, CaseNumber: {case_number}, 與 {resp_staff} (主要案件: {second_main_case})")

    staff_days = {staff: len(days) for staff, days in staff_days.items()}

    # 顯示溫?邦的計算步驟
    st.subheader("溫?邦 本區協作節數計算步驟")
    if wen_collaboration_log:
        for log in wen_collaboration_log:
            st.write(log)
    else:
        st.write("無協作記錄")
    st.write(f"溫?邦 本區協作總節數: {staff_total_stats.get('溫?邦', {}).get('協作', 0)}")
    st.write(f"溫?邦 外區協作總節數: {staff_outside_stats.get('溫?邦', {}).get('協作', 0)}")

    st.subheader("溫?邦 工作日數計算步驟")
    if wen_days_log:
        for log in wen_days_log:
            st.write(log)
    st.write(f"溫?邦 總工作日數: {staff_days.get('溫?邦', 0)}")

    return staff_total_stats, staff_outside_stats, staff_days, activity_type_stats

def main():
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

        staff_total_stats, staff_outside_stats, staff_days, activity_type_stats = calculate_staff_stats(df)
        if staff_total_stats is None:
            st.error("統計計算失敗，請檢查錯誤訊息")
            return

        st.subheader("本區統計（總個人與協作次數）")
        total_stats_df = pd.DataFrame(staff_total_stats).T
        total_stats_df.columns = ['個人 (節)', '協作 (節)']
        st.table(total_stats_df)

        st.subheader("外區統計")
        outside_stats_df = pd.DataFrame(staff_outside_stats).T
        outside_stats_df.columns = ['個人 (節)', '協作 (節)']
        st.table(outside_stats_df)

        st.subheader("員工工作日數統計")
        days_df = pd.DataFrame.from_dict(staff_days, orient='index', columns=['工作日數'])
        st.table(days_df)

        st.subheader("活動類型統計")
        activity_df = pd.DataFrame.from_dict(activity_type_stats, orient='index', columns=['次數'])
        st.table(activity_df)

if __name__ == "__main__":
    main()
