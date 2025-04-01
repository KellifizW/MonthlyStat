import streamlit as st
import pandas as pd
import io

# 預定義的欄位名稱（根據你的檔案）
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

# 必要欄位（用於統計）
REQUIRED_COLUMNS = ['RespStaff', '2ndRespStaffName', 'CaseNumber', 'NumberOfSession', 'ServiceDate']

# 函數：使用 big5hkscs 讀取 CSV
def read_csv_with_big5(file):
    file.seek(0)
    
    encoding = 'big5hkscs'
    separators = [',', '\t']
    
    # 檢測分隔符
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
        
        if 'NumberOfSession' in df.columns:
            df['NumberOfSession'] = pd.to_numeric(df['NumberOfSession'], errors='coerce')
            if df['NumberOfSession'].isnull().any():
                st.warning("NumberOfSession 欄位中存在無效數值，已轉換為 0")
                df['NumberOfSession'] = df['NumberOfSession'].fillna(0).astype(int)
        return df, encoding
    except Exception as e:
        st.error(f"無法讀取檔案，請檢查檔案是否為有效的 CSV")
        st.write(f"錯誤詳情: {str(e)}")
        return None, None

# 函數：計算統計數據
def calculate_staff_stats(df):
    missing_columns = [col for col in REQUIRED_COLUMNS if col in df.columns]
    if missing_columns:
        st.error(f"缺少必要欄位: {missing_columns}")
        return None, None, None, None

    for col in REQUIRED_COLUMNS:
        if df[col].isnull().any():
            st.warning(f"{col} 欄位中存在空值，將跳過相關行")

    staff_total_stats = {}
    staff_outside_stats = {}
    staff_days = {}  # 每個員工的工作日數
    activity_type_stats = df['活動類型'].value_counts().to_dict()  # 活動類型統計

    try:
        staff_case_counts = df.groupby('RespStaff')['CaseNumber'].value_counts().unstack(fill_value=0)
        staff_main_case = staff_case_counts.idxmax(axis=1).to_dict()
    except Exception as e:
        st.error(f"計算本區 CaseNumber 時發生錯誤: {str(e)}")
        return None, None, None, None

    for index, row in df.iterrows():
        resp_staff = row['RespStaff']
        case_number = row['CaseNumber']
        service_date = row['ServiceDate']

        if pd.isna(resp_staff) or pd.isna(case_number) or pd.isna(service_date):
            continue

        # 初始化員工統計
        if resp_staff not in staff_total_stats:
            staff_total_stats[resp_staff] = {'個人': 0, '協作': 0}
            staff_outside_stats[resp_staff] = {'個人': 0, '協作': 0}
            staff_days[resp_staff] = set()  # 使用集合記錄唯一日期

        # 無論本區還是外區，都記錄主要員工的工作日
        staff_days[resp_staff].add(service_date)

        try:
            second_staff = row['2ndRespStaffName'] if pd.notna(row['2ndRespStaffName']) else None
        except Exception as e:
            st.error(f"行 {index} 處理 2ndRespStaffName 時發生錯誤: {str(e)}")
            continue

        is_collaboration = bool(second_staff)
        main_case = staff_main_case.get(resp_staff)

        if main_case is None:
            continue

        if not is_collaboration:
            if case_number == main_case:
                staff_total_stats[resp_staff]['個人'] += 1
            else:
                staff_outside_stats[resp_staff]['個人'] += 1
                # 外區個人節數也已記錄日期，無需額外操作
        else:
            staff_total_stats[resp_staff]['協作'] += 1
            if second_staff:
                if second_staff not in staff_total_stats:
                    staff_total_stats[second_staff] = {'個人': 0, '協作': 0}
                    staff_outside_stats[second_staff] = {'個人': 0, '協作': 0}
                    staff_days[second_staff] = set()
                staff_total_stats[second_staff]['協作'] += 1
                staff_days[second_staff].add(service_date)  # 協作員工記錄日期

                if case_number != main_case:
                    staff_outside_stats[resp_staff]['協作'] += 1
                    staff_outside_stats[second_staff]['協作'] += 1
                    # 外區協作節數也已記錄日期，無需額外操作

    # 將集合轉換為日數
    staff_days = {staff: len(days) for staff, days in staff_days.items()}

    return staff_total_stats, staff_outside_stats, staff_days, activity_type_stats

# Streamlit 主介面
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

        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, encoding=used_encoding)
        st.download_button(
            label="下載解析後的 CSV",
            data=csv_buffer.getvalue(),
            file_name="parsed_data.csv",
            mime="text/csv"
        )

        staff_total_stats, staff_outside_stats, staff_days, activity_type_stats = calculate_staff_stats(df)
        if staff_total_stats is None or staff_outside_stats is None:
            st.error("統計計算失敗，請檢查錯誤訊息")
            return

        # 本區統計
        st.subheader("本區統計（總個人與協作次數）")
        total_stats_df = pd.DataFrame(staff_total_stats).T
        total_stats_df.columns = ['個人 (節)', '協作 (節)']
        st.table(total_stats_df)

        # 外區統計
        st.subheader("外區統計")
        outside_stats_df = pd.DataFrame(staff_outside_stats).T
        outside_stats_df.columns = ['個人 (節)', '協作 (節)']
        st.table(outside_stats_df)

        # 員工日數統計
        st.subheader("員工工作日數統計")
        days_df = pd.DataFrame.from_dict(staff_days, orient='index', columns=['工作日數'])
        st.table(days_df)

        # 活動類型統計
        st.subheader("活動類型統計")
        activity_df = pd.DataFrame.from_dict(activity_type_stats, orient='index', columns=['次數'])
        st.table(activity_df)

if __name__ == "__main__":
    main()
