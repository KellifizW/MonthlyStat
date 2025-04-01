import streamlit as st
import pandas as pd
import io
import chardet
import magic
import traceback

# 預定義的欄位名稱
EXPECTED_COLUMNS = [
    'CaseNumber', 'RespStaffLogin', 'RespStaff', '2ndRespStaffLoginID', '2ndRespStaffName',
    'CoachedStaffLogin', 'CoachedStaff', 'Dept', 'Id', 'ServiceDate', 'ServiceTime',
    'CaseName', 'HomeName', 'NumberOfSession', 'NumberOfParticipant(Without Volunteer Count)',
    '活動編號', '活動類型'
]

# 必要欄位（用於統計）
REQUIRED_COLUMNS = ['RespStaff', '2ndRespStaffName', 'CaseNumber', 'NumberOfSession']

# 函數：檢測檔案編碼和類型
def detect_file_info(file):
    file.seek(0)
    raw_data = file.read(1024)
    file.seek(0)
    
    encoding_result = chardet.detect(raw_data)
    detected_encoding = encoding_result['encoding']
    encoding_confidence = encoding_result['confidence']
    
    mime_detector = magic.Magic(mime=True)
    file_type = mime_detector.from_buffer(raw_data)
    
    return {
        'detected_encoding': detected_encoding,
        'encoding_confidence': encoding_confidence,
        'file_type': file_type,
        'sample_content': raw_data[:100].decode(detected_encoding, errors='replace') if detected_encoding else "無法解碼"
    }

# 函數：兼容多種編碼的 CSV 讀取
def read_csv_with_big5(file, manual_encoding=None):
    file.seek(0)
    
    encodings = ['big5', 'utf-8', 'gbk']
    if manual_encoding:
        encodings = [manual_encoding] + [enc for enc in encodings if enc != manual_encoding]
    
    bom = file.read(3)
    if bom == b'\xef\xbb\xbf':
        encoding = 'utf-8'
        sample = file.read(1024).decode(encoding)
    else:
        file.seek(0)
        for enc in encodings:
            try:
                file.seek(0)
                sample = file.read(1024).decode(enc)
                encoding = enc
                break
            except UnicodeDecodeError:
                continue
        else:
            file_info = detect_file_info(file)
            st.error("無法讀取檔案，所有嘗試的編碼均失敗")
            st.write("檔案資訊：")
            st.write(f"- 檢測到的編碼: {file_info['detected_encoding']} (信心度: {file_info['encoding_confidence']:.2%})")
            st.write(f"- 檔案類型: {file_info['file_type']}")
            st.write(f"- 前 100 字節內容: {file_info['sample_content']}")
            return None, None
    
    separators = [',', '\t']
    separator = max(separators, key=lambda sep: sample.count(sep))

    for enc in encodings:
        try:
            file.seek(0)
            if enc == 'utf-8' and bom == b'\xef\xbb\xbf':
                file.read(3)
            df = pd.read_csv(file, encoding=enc, sep=separator, on_bad_lines='warn')
            
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
            return df, enc
        except UnicodeDecodeError as e:
            st.warning(f"編碼 {enc} 解碼失敗: {str(e)}")
            continue
        except Exception as e:
            file_info = detect_file_info(file)
            st.error("無法讀取檔案，請檢查檔案是否為有效的 CSV")
            st.write("檔案資訊：")
            st.write(f"- 檢測到的編碼: {file_info['detected_encoding']} (信心度: {file_info['encoding_confidence']:.2%})")
            st.write(f"- 檔案類型: {file_info['file_type']}")
            st.write(f"- 前 100 字節內容: {file_info['sample_content']}")
            st.write(f"錯誤詳情: {str(e)}")
            st.write("完整錯誤堆棧:")
            st.write(traceback.format_exc())
            return None, None
    
    file_info = detect_file_info(file)
    st.error("無法讀取檔案，所有嘗試的編碼均失敗")
    st.write("檔案資訊：")
    st.write(f"- 檢測到的編碼: {file_info['detected_encoding']} (信心度: {file_info['encoding_confidence']:.2%})")
    st.write(f"- 檔案類型: {file_info['file_type']}")
    st.write(f"- 前 100 字節內容: {file_info['sample_content']}")
    return None, None

# 函數：計算本區和外區統計
def calculate_staff_stats(df):
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        st.error(f"缺少必要欄位: {missing_columns}")
        return None, None

    for col in REQUIRED_COLUMNS:
        if df[col].isnull().any():
            st.warning(f"{col} 欄位中存在空值，將跳過相關行")

    staff_total_stats = {}
    staff_outside_stats = {}

    try:
        staff_case_counts = df.groupby('RespStaff')['CaseNumber'].value_counts().unstack(fill_value=0)
        staff_main_case = staff_case_counts.idxmax(axis=1).to_dict()
    except Exception as e:
        st.error(f"計算本區 CaseNumber 時發生錯誤: {str(e)}")
        return None, None

    for index, row in df.iterrows():
        resp_staff = row['RespStaff']
        case_number = row['CaseNumber']

        if pd.isna(resp_staff) or pd.isna(case_number):
            continue

        if resp_staff not in staff_total_stats:
            staff_total_stats[resp_staff] = {'個人': 0, '協作': 0}
            staff_outside_stats[resp_staff] = {'個人': 0, '協作': 0}

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
        else:
            staff_total_stats[resp_staff]['協作'] += 1
            if second_staff:
                if second_staff not in staff_total_stats:
                    staff_total_stats[second_staff] = {'個人': 0, '協作': 0}
                    staff_outside_stats[second_staff] = {'個人': 0, '協作': 0}
                staff_total_stats[second_staff]['協作'] += 1

                if case_number != main_case:
                    staff_outside_stats[resp_staff]['協作'] += 1
                    staff_outside_stats[second_staff]['協作'] += 1

    return staff_total_stats, staff_outside_stats

# Streamlit 主介面
def main():
    st.title("員工活動統計工具 (支援多種編碼)")
    st.write("請上傳使用 Big5、UTF-8 或其他編碼的 CSV 檔案以計算員工的本區與外區統計結果。")

    uploaded_file = st.file_uploader("選擇 CSV 檔案", type=["csv"])
    manual_encoding = st.selectbox("手動指定編碼（可選）", [None, 'big5', 'utf-8', 'gbk', 'utf-16', 'windows-1252'], index=0)

    if uploaded_file is not None:
        st.write("檔案已上傳，名稱:", uploaded_file.name)
        df, used_encoding = read_csv_with_big5(uploaded_file, manual_encoding)
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

if __name__ == "__main__":
    main()
