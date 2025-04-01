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

# 必要欄位（用於統計）
REQUIRED_COLUMNS = ['RespStaff', '2ndRespStaffName', 'CaseNumber', 'NumberOfSession']

# 函數：兼容多種編碼的 CSV 讀取
def read_csv_with_big5(file):
    st.write("開始讀取 CSV 檔案（支援 Big5、UTF-8 BOM 和 UTF-8）...")
    file.seek(0)
    
    encodings = ['big5', 'utf-8', 'gbk']
    
    bom = file.read(3)
    if bom == b'\xef\xbb\xbf':  # UTF-8 BOM
        encoding = 'utf-8'
        st.write("檢測到 UTF-8 BOM，將使用 UTF-8 編碼")
        sample = file.read(1024).decode(encoding)
    else:
        file.seek(0)
        for enc in encodings:
            try:
                file.seek(0)
                sample = file.read(1024).decode(enc)
                encoding = enc
                st.write(f"檢測到可能的編碼：{enc}")
                break
            except UnicodeDecodeError:
                st.write(f"{enc} 解碼失敗，嘗試下一個編碼...")
        else:
            st.error("無法確定編碼，檔案可能損壞或使用未知編碼")
            file.seek(0)
            st.write("檔案前 500 字節（以 latin1 強制解碼）：", file.read()[:500].decode('latin1'))
            return None, None
    
    separators = [',', '\t']
    separator = max(separators, key=lambda sep: sample.count(sep))
    st.write(f"檢測到分隔符：{separator}")

    for enc in encodings:
        try:
            file.seek(0)
            if enc == 'utf-8' and bom == b'\xef\xbb\xbf':
                file.read(3)  # 跳過 BOM
            df = pd.read_csv(file, encoding=enc, sep=separator, on_bad_lines='warn')
            st.write(f"成功使用 {enc} 編碼讀取檔案（分隔符：{separator}）")
            st.write(f"解析出的欄位數量: {len(df.columns)}")
            
            st.write("CSV 文件的原始欄位名稱：", list(df.columns))
            
            missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
            if missing_columns:
                st.error(f"CSV 文件缺少必要欄位: {missing_columns}")
                st.write("請確認檔案欄位名稱與預期一致")
                return None, None
            
            available_columns = [col for col in EXPECTED_COLUMNS if col in df.columns]
            df = df[available_columns]
            st.write(f"保留的欄位數量: {len(df.columns)}，欄位名稱: {available_columns}")
            
            st.write("檢查 NumberOfSession 欄位原始數據（前 5 行）：", df['NumberOfSession'].head().to_dict())
            
            st.write("轉換 NumberOfSession 欄位為數值...")
            if 'NumberOfSession' in df.columns:
                df['NumberOfSession'] = pd.to_numeric(df['NumberOfSession'], errors='coerce')
                if df['NumberOfSession'].isnull().any():
                    st.warning("NumberOfSession 欄位中存在無效數值，已轉換為 NaN")
                    invalid_rows = df[df['NumberOfSession'].isnull()][['CaseNumber', 'RespStaff', 'NumberOfSession']]
                    st.write("無效數據行：", invalid_rows.to_dict())
                    df['NumberOfSession'] = df['NumberOfSession'].fillna(0).astype(int)
                    st.write("已將 NaN 值替換為 0")
            return df, enc
        except UnicodeDecodeError as e:
            st.error(f"無法使用 {enc} 編碼讀取檔案: {str(e)}")
        except Exception as e:
            st.error(f"解析錯誤: {str(e)}")
            raise
    
    st.error("無法讀取檔案，所有嘗試的編碼均失敗")
    return None, None

# 函數：計算本區和外區統計
def calculate_staff_stats(df):
    st.write("檔案實際欄位名稱:", list(df.columns))
    st.write("程式預期的必要欄位:", REQUIRED_COLUMNS)
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        raise ValueError(f"缺少必要欄位: {missing_columns}")

    st.write("檢查數據完整性（是否有空值）：")
    for col in REQUIRED_COLUMNS:
        if df[col].isnull().any():
            st.warning(f"{col} 欄位中存在空值，將跳過相關行")
            st.write(f"{col} 空值行：", df[df[col].isnull()][REQUIRED_COLUMNS].to_dict())

    staff_total_stats = {}
    staff_outside_stats = {}

    try:
        staff_case_counts = df.groupby('RespStaff')['CaseNumber'].value_counts().unstack(fill_value=0)
        staff_main_case = staff_case_counts.idxmax(axis=1).to_dict()
        st.write("每位員工的本區 (最高頻次 CaseNumber):", staff_main_case)
    except Exception as e:
        st.error(f"計算本區 CaseNumber 時發生錯誤: {str(e)}")
        return None, None

    st.write("開始逐行計算統計...")
    for index, row in df.iterrows():
        resp_staff = row['RespStaff']
        second_staff = row['2ndRespStaffName'] if pd.notna(row['2ndRespStaffName']) else None
        case_number = row['CaseNumber']
        number_of_session = row['NumberOfSession']

        if pd.isna(resp_staff) or pd.isna(case_number):
            st.warning(f"行 {index} 缺少 RespStaff 或 CaseNumber，跳過: {row[REQUIRED_COLUMNS].to_dict()}")
            continue

        if resp_staff not in staff_total_stats:
            staff_total_stats[resp_staff] = {'個人': 0, '協作': 0}
            staff_outside_stats[resp_staff] = {'個人': 0, '協作': 0}

        is_collaboration = bool(second_staff)
        main_case = staff_main_case.get(resp_staff, None)
        sessions = int(number_of_session)

        try:
            if not is_collaboration:
                staff_total_stats[resp_staff]['個人'] += sessions
                if main_case and case_number != main_case:
                    staff_outside_stats[resp_staff]['個人'] += sessions
                st.write(f"行 {index}: {resp_staff} 個人 +{sessions} (CaseNumber: {case_number}, 本區: {main_case})")
            else:
                staff_total_stats[resp_staff]['協作'] += sessions
                if second_staff:
                    if second_staff not in staff_total_stats:
                        staff_total_stats[second_staff] = {'個人': 0, '協作': 0}
                    staff_total_stats[second_staff]['協作'] += sessions

                    if main_case and case_number != main_case:
                        staff_outside_stats[resp_staff]['協作'] += sessions
                        if second_staff not in staff_outside_stats:
                            staff_outside_stats[second_staff] = {'個人': 0, '協作': 0}
                        staff_outside_stats[second_staff]['協作'] += sessions
                st.write(f"行 {index}: {resp_staff} 協作 +{sessions}, {second_staff} 協作 +{sessions} (CaseNumber: {case_number}, 本區: {main_case})")
        except Exception as e:
            st.error(f"處理行 {index} 時發生錯誤: {str(e)}，數據: {row[REQUIRED_COLUMNS].to_dict()}")
            continue

    st.write("計算完成，返回統計結果")
    return staff_total_stats, staff_outside_stats

# Streamlit 主介面
def main():
    st.title("員工活動統計工具 (支援多種編碼)")
    st.write("請上傳使用 Big5、UTF-8 或其他編碼的 CSV 檔案以計算員工的本區與外區統計結果。")

    uploaded_file = st.file_uploader("選擇 CSV 檔案", type=["csv"])

    if uploaded_file is not None:
        st.write("檔案已上傳，名稱:", uploaded_file.name)
        try:
            df, used_encoding = read_csv_with_big5(uploaded_file)
            if df is None:
                st.error("無法讀取檔案，請檢查檔案是否為有效的 CSV")
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

            staff_total_stats, staff_outside_stats = calculate_staff_stats(df)
            if staff_total_stats is None or staff_outside_stats is None:
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

        except ValueError as ve:
            st.error(f"錯誤: {str(ve)}")
        except Exception as e:
            st.error(f"發生錯誤: {str(e)}")
            st.write("請檢查檔案是否為有效的 CSV 格式，並包含必要欄位")
    else:
        st.info("請上傳一個 CSV 檔案以開始分析。")

if __name__ == "__main__":
    main()
