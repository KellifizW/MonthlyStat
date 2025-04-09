import streamlit as st
import pandas as pd
import requests
from io import StringIO
import re
import graph  # 引入 graph.py

# 設置頁面為寬屏模式
st.set_page_config(layout="wide")

# GitHub Raw URL
RAW_URL = "https://raw.githubusercontent.com/KellifizW/MonthlyStat/main/homelist.csv"

# 定義必要欄位
REQUIRED_COLUMNS = ['RespStaff', '2ndRespStaffName', 'HomeName', 'ServiceDate']

# 名稱轉換字典
NAME_CONVERSION = {
    '溫?邦': 'Pong',
    '譚惠凌': 'Ling',
    '陳發成': 'Jack',
    '林振聲': 'Mike',
    '黃瑞霞': 'Peppy',
    '曾嘉欣': 'Kama',
    '徐家兒': 'Kayi'
}

# 初始化 session_state
if 'uploaded_df' not in st.session_state:
    st.session_state['uploaded_df'] = None
if 'used_encoding' not in st.session_state:
    st.session_state['used_encoding'] = None

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

# 判斷區域並返回員工的區域狀態
def check_local(row, github_df):
    home_number = extract_home_number(row['HomeName'])
    resp_staff = row['RespStaff'] if pd.notna(row['RespStaff']) else None
    second_staff = row['2ndRespStaffName'] if pd.notna(row['2ndRespStaffName']) else None

    if home_number is None:
        return {'resp_region': '外區', 'second_region': '外區' if second_staff else None}

    matching_homes = github_df[github_df['Home'].astype(str) == str(home_number)]
    if matching_homes.empty:
        return {'resp_region': '外區', 'second_region': '外區' if second_staff else None}

    local_staff = set()
    for _, home_row in matching_homes.iterrows():
        if pd.notna(home_row['staff1']):
            local_staff.add(home_row['staff1'])
        if pd.notna(home_row['staff2']):
            local_staff.add(home_row['staff2'])

    resp_region = '本區' if resp_staff in local_staff else '外區'
    second_region = '本區' if second_staff in local_staff else '外區' if second_staff else None

    return {'resp_region': resp_region, 'second_region': second_region}

# 轉換員工名稱
def convert_name(name):
    return NAME_CONVERSION.get(name, name) if pd.notna(name) else name

# 計算員工統計（含本區總共和全部總共）
def calculate_staff_stats(df, github_df):
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        st.error(f"缺少必要欄位: {missing_columns}")
        return None

    staff_stats = {}
    staff_days = {}

    for index, row in df.iterrows():
        resp_staff = convert_name(row['RespStaff'])
        second_staff = convert_name(row['2ndRespStaffName']) if pd.notna(row['2ndRespStaffName']) else None
        service_date = row['ServiceDate']

        if pd.isna(resp_staff) or pd.isna(service_date):
            continue

        if resp_staff not in staff_stats:
            staff_stats[resp_staff] = {
                '本區單獨': 0, '本區協作': 0, '外區單獨': 0, '外區協作': 0
            }
            staff_days[resp_staff] = set()
        if second_staff and second_staff not in staff_stats:
            staff_stats[second_staff] = {
                '本區單獨': 0, '本區協作': 0, '外區單獨': 0, '外區協作': 0
            }
            staff_days[second_staff] = set()

        staff_days[resp_staff].add(service_date)
        if second_staff:
            staff_days[second_staff].add(service_date)

        regions = check_local(row, github_df)
        resp_region = regions['resp_region']
        second_region = regions['second_region']

        if not second_staff:
            if resp_region == '本區':
                staff_stats[resp_staff]['本區單獨'] += 1
            else:
                staff_stats[resp_staff]['外區單獨'] += 1
        else:
            if resp_region == '本區':
                staff_stats[resp_staff]['本區協作'] += 1
            else:
                staff_stats[resp_staff]['外區協作'] += 1
            if second_region == '本區':
                staff_stats[second_staff]['本區協作'] += 1
            else:
                staff_stats[second_staff]['外區協作'] += 1

    for staff in staff_stats:
        staff_stats[staff]['外出日數'] = len(staff_days[staff])
        staff_stats[staff]['本區總共'] = staff_stats[staff]['本區單獨'] + staff_stats[staff]['本區協作']
        staff_stats[staff]['全部總共'] = (staff_stats[staff]['本區總共'] + 
                                         staff_stats[staff]['外區單獨'] + 
                                         staff_stats[staff]['外區協作'])

    return staff_stats, staff_days

# 計算分區統計節數並返回詳細記錄（含人次統計）
def calculate_region_stats(df, github_df):
    region_stats = {
        'Ling': {'count': 0, 'homes': set(), 'records': [], 'participants': 0},
        'Mike': {'count': 0, 'homes': set(), 'records': [], 'participants': 0},
        'Pong': {'count': 0, 'homes': set(), 'records': [], 'participants': 0},
        'Peppy': {'count': 0, 'homes': set(), 'records': [], 'participants': 0}
    }

    has_participants_column = 'NumberOfParticipant(Without Volunteer Count)' in df.columns

    for index, row in df.iterrows():
        home_number = extract_home_number(row['HomeName'])
        if home_number is None:
            continue

        matching_homes = github_df[github_df['Home'].astype(str) == str(home_number)]
        if matching_homes.empty:
            continue

        staff1 = matching_homes.iloc[0]['staff1']
        if pd.isna(staff1) or staff1 not in region_stats:
            continue

        region_stats[staff1]['count'] += 1
        region_stats[staff1]['homes'].add(home_number)
        record = {
            'RespStaff': row['RespStaff'],
            'ServiceDate': row['ServiceDate'],
            'HomeName': row['HomeName']
        }
        region_stats[staff1]['records'].append(record)

        if has_participants_column and pd.notna(row['NumberOfParticipant(Without Volunteer Count)']):
            try:
                participants = int(row['NumberOfParticipant(Without Volunteer Count)'])
                region_stats[staff1]['participants'] += participants
            except ValueError:
                continue

    total_sessions = sum(region['count'] for region in region_stats.values())
    total_participants = sum(region['participants'] for region in region_stats.values()) if has_participants_column else None
    return region_stats, total_sessions, total_participants

# 獲取員工的詳細記錄
def get_staff_details(df, staff_name):
    solo_records = []
    collab_records = []
    solo_days = set()
    collab_days = set()

    for index, row in df.iterrows():
        resp_staff = convert_name(row['RespStaff'])
        second_staff = convert_name(row['2ndRespStaffName']) if pd.notna(row['2ndRespStaffName']) else None
        service_date = row['ServiceDate']
        home_name = row['HomeName']

        if resp_staff == staff_name and not second_staff:
            solo_records.append({'ServiceDate': service_date, 'HomeName': home_name})
            solo_days.add(service_date)
        elif resp_staff == staff_name and second_staff:
            collab_records.append({'ServiceDate': service_date, 'HomeName': home_name, 'Collaborator': second_staff})
            collab_days.add(service_date)
        elif second_staff == staff_name:
            collab_records.append({'ServiceDate': service_date, 'HomeName': home_name, 'Collaborator': resp_staff})
            collab_days.add(service_date)

    all_days = solo_days.union(collab_days)
    return {
        'solo_records': solo_records,
        'collab_records': collab_records,
        'solo_days': sorted(solo_days),
        'collab_days': sorted(collab_days),
        'all_days': sorted(all_days)
    }

# 列表頁（移除列表詳情）
def list_page():
    st.title("GitHub homelist.csv 列表")
    st.write("從 GitHub 儲存庫讀取並顯示 homelist.csv 的內容。")

    df = get_github_csv_data(RAW_URL)
    if df is not None:
        st.subheader("homelist.csv 內容")
        st.dataframe(df)

# 自定義樣式函數（為員工統計表設置顏色）
def style_staff_table(df):
    def row_style(row):
        if row.name == 'Ling' or row.name == 'Kayi':
            return ['background-color: #FFF5BA'] * len(row)  # 粉黃色
        elif row.name == 'Mike':
            return ['background-color: #FFE6E6'] * len(row)  # 更淺的粉紅色
        elif row.name == 'Pong' or row.name == 'Jack':
            return ['background-color: #CCFFCC'] * len(row)  # 粉綠色
        elif row.name == 'Peppy' or row.name == 'Kama':
            return ['background-color: #CCE5FF'] * len(row)  # 粉藍色
        return [''] * len(row)
    
    return df.style.apply(row_style, axis=1)

# 外出統計程式頁
def outing_stats_page():
    st.title("外出統計程式")
    st.write("請上傳 CSV 檔案，程式將根據 GitHub 的 homelist.csv 計算每位員工的本區與外區單獨及協作節數，並顯示分區統計節數（使用 Big5HKSCS 編碼）。")

    # 檢查是否已經有上傳的數據
    if st.session_state['uploaded_df'] is None:
        uploaded_file = st.file_uploader("選擇 CSV 檔案", type=["csv"], key="outing_uploader")
        if uploaded_file is not None:
            st.write("檔案已上傳，名稱:", uploaded_file.name)
            uploaded_df, used_encoding = read_csv_with_big5(uploaded_file)
            if uploaded_df is None:
                return
            # 儲存到 session_state
            st.session_state['uploaded_df'] = uploaded_df
            st.session_state['used_encoding'] = used_encoding
    else:
        st.write("已使用之前上傳的檔案，若需更換請重新上傳。")
        uploaded_file = st.file_uploader("選擇 CSV 檔案", type=["csv"], key="outing_uploader")
        if uploaded_file is not None:
            st.write("檔案已上傳，名稱:", uploaded_file.name)
            uploaded_df, used_encoding = read_csv_with_big5(uploaded_file)
            if uploaded_df is None:
                return
            # 更新 session_state
            st.session_state['uploaded_df'] = uploaded_df
            st.session_state['used_encoding'] = used_encoding

    # 使用 session_state 中的數據
    uploaded_df = st.session_state['uploaded_df']
    used_encoding = st.session_state['used_encoding']

    if uploaded_df is not None:
        # 轉換員工名稱
        uploaded_df['RespStaff'] = uploaded_df['RespStaff'].apply(convert_name)
        uploaded_df['2ndRespStaffName'] = uploaded_df['2ndRespStaffName'].apply(convert_name)

        st.write(f"檔案成功解析，使用編碼: {used_encoding}")

        github_df = get_github_csv_data(RAW_URL)
        if github_df is None:
            return

        required_uploaded_cols = ['HomeName', 'RespStaff', '2ndRespStaffName', 'ServiceDate']
        required_github_cols = ['Home', 'staff1', 'staff2']
        missing_uploaded = [col for col in required_uploaded_cols if col not in uploaded_df.columns]
        missing_github = [col for col in required_github_cols if col not in github_df.columns]

        if missing_uploaded:
            st.error(f"上傳的 CSV 缺少必要欄位: {missing_uploaded}")
            return
        if missing_github:
            st.error(f"GitHub 的 homelist.csv 缺少必要欄位: {missing_github}")
            return

        # 應用區域判斷並記錄到數據框
        uploaded_df[['RespRegion', 'SecondRegion']] = uploaded_df.apply(
            lambda row: pd.Series(check_local(row, github_df)), axis=1
        )

        # 計算員工統計
        staff_stats, staff_days = calculate_staff_stats(uploaded_df, github_df)
        if staff_stats is None:
            st.error("統計計算失敗，請檢查錯誤訊息")
            return

        # 計算分區統計節數
        region_stats, total_sessions, total_participants = calculate_region_stats(uploaded_df, github_df)

        # 並排顯示員工統計表和分區統計節數（調整比例）
        col1, col2 = st.columns([7, 3])  # 員工統計表 70%，分區統計節數 30%

        with col1:
            st.subheader("員工統計表")
            stats_df = pd.DataFrame(staff_stats).T
            stats_df = stats_df[['本區單獨', '本區協作', '本區總共', '外區單獨', '外區協作', '全部總共', '外出日數']]
            stats_df.index.name = '員工'
            # 自定義排序
            desired_order = ['Ling', 'Mike', 'Pong', 'Peppy', 'Kayi', 'Jack', 'Kama']
            existing_staff = [staff for staff in desired_order if staff in stats_df.index]
            stats_df = stats_df.reindex(existing_staff)
            # 應用樣式
            styled_df = style_staff_table(stats_df)
            st.dataframe(styled_df, height=300)

        with col2:
            st.subheader("分區統計節數")
            region_data = {
                '分區': list(region_stats.keys()),
                '節數': [region_stats[region]['count'] for region in region_stats]
            }
            if 'NumberOfParticipant(Without Volunteer Count)' in uploaded_df.columns:
                region_data['人次'] = [region_stats[region]['participants'] for region in region_stats]
            region_df = pd.DataFrame(region_data)
            region_df.loc[len(region_df)] = ['總計', total_sessions] + ([total_participants] if '人次' in region_df.columns else [])
            st.dataframe(region_df, height=300)

        # 並排顯示 ServiceStatus 和 活動類型 統計
        col1, col2 = st.columns(2)

        with col1:
            st.write("**ServiceStatus 統計：**")
            if 'ServiceStatus' in uploaded_df.columns:
                status_counts = uploaded_df['ServiceStatus'].value_counts()
                for status, count in status_counts.items():
                    st.write(f"{status}: {count} 次")
                st.write(f"總計: {status_counts.sum()} 次")
            else:
                st.write("無此欄位")

            # 新增 NumberOfSession 統計
            st.write("**NumberOfSession 統計：**")
            if 'NumberOfSession' in uploaded_df.columns:
                session_counts = uploaded_df['NumberOfSession'].value_counts()
                for session, count in session_counts.items():
                    st.write(f"{session}: {count} 次")
                st.write(f"總計: {session_counts.sum()} 次")
            else:
                st.write("無此欄位")

        with col2:
            st.write("**活動類型 統計：**")
            if '活動類型' in uploaded_df.columns:
                type_counts = uploaded_df['活動類型'].value_counts().reset_index()
                type_counts.columns = ['活動類型', '次數']
                type_counts.loc[len(type_counts)] = ['總計', type_counts['次數'].sum()]
                st.dataframe(type_counts, height=200)
            else:
                st.write("無此欄位")

        # 分區詳細統計（僅在選擇時顯示）
        st.subheader("分區詳細統計")
        region_list = ['選擇分區'] + list(region_stats.keys())
        selected_region = st.selectbox("選擇分區", region_list, index=0, key="region_select")
        
        if selected_region != '選擇分區':
            participants_text = f"，人次: {region_stats[selected_region]['participants']}" if 'NumberOfParticipant(Without Volunteer Count)' in uploaded_df.columns else ""
            st.write(f"### {selected_region} 分區（{region_stats[selected_region]['count']} 節{participants_text}）")
            homes = sorted(region_stats[selected_region]['homes'])
            st.write(f"相關院舍（staff1 = {selected_region}）：{', '.join(homes)}")
            st.write("記錄清單：")
            if region_stats[selected_region]['records']:
                records_df = pd.DataFrame(region_stats[selected_region]['records'])
                records_df = records_df[['RespStaff', 'ServiceDate', 'HomeName']]
                records_df.columns = ['負責員工', '活動日期', '院舍名稱']
                st.dataframe(records_df, height=300)
            else:
                st.write("無記錄")

        # 員工詳細統計（僅在選擇時顯示）
        st.subheader("員工詳細統計")
        staff_list = ['選擇員工'] + list(staff_stats.keys())
        selected_staff = st.selectbox("選擇員工", staff_list, index=0, key="staff_select")

        if selected_staff != '選擇員工':
            details = get_staff_details(uploaded_df, selected_staff)
            st.write(f"### {selected_staff}")
            
            st.write("**單獨記錄：**")
            if details['solo_records']:
                solo_df = pd.DataFrame(details['solo_records'])
                solo_df.columns = ['活動日期', '院舍名稱']
                st.dataframe(solo_df, height=200)
            else:
                st.write("無單獨記錄")

            st.write("**協作記錄：**")
            if details['collab_records']:
                collab_df = pd.DataFrame(details['collab_records'])
                collab_df.columns = ['活動日期', '院舍名稱', '協作者']
                st.dataframe(collab_df, height=200)
            else:
                st.write("無協作記錄")

            st.write("**不重複日期：**")
            st.write(f"單獨：{', '.join(details['solo_days'])} → {len(details['solo_days'])} 天")
            st.write(f"協作：{', '.join(details['collab_days'])} → {len(details['collab_days'])} 天")
            st.write(f"總計：{', '.join(details['all_days'])} → {len(details['all_days'])} 天")

# 統計圖頁面
def stats_chart_page():
    st.title("統計圖")
    st.write("此頁面顯示活動類型的統計圖表。")

    # 檢查是否有上傳的數據
    if st.session_state['uploaded_df'] is None:
        st.warning("請先在「外出統計程式」頁面上傳 CSV 檔案以生成圖表。")
        return

    uploaded_df = st.session_state['uploaded_df']

    if '活動類型' in uploaded_df.columns:
        type_counts = uploaded_df['活動類型'].value_counts().reset_index()
        type_counts.columns = ['活動類型', '次數']
        type_counts.loc[len(type_counts)] = ['總計', type_counts['次數'].sum()]

        # 提取 ServiceDate 欄位的年份和月份
        if 'ServiceDate' in uploaded_df.columns:
            try:
                # 將 ServiceDate 轉換為 datetime 格式
                uploaded_df['ServiceDate'] = pd.to_datetime(uploaded_df['ServiceDate'], errors='coerce')
                # 提取年份和月份（假設數據中所有日期在同一年和同一月）
                year = uploaded_df['ServiceDate'].dt.year.iloc[0]
                month = uploaded_df['ServiceDate'].dt.month.iloc[0]
                title = f"{year}年{month}月 份活動內容"
            except Exception as e:
                st.warning(f"無法解析 ServiceDate 欄位：{str(e)}，使用默認標題。")
                title = "2025年1月 份活動內容"
        else:
            st.warning("上傳的 CSV 中無 ServiceDate 欄位，使用默認標題。")
            title = "2025年1月 份活動內容"
        
        # 顯示圖表
        st.write("**活動類型分佈圖：**")
        fig = graph.create_activity_type_donut_chart(type_counts, title)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("上傳的 CSV 中無「活動類型」欄位，無法生成圖表。")

# 主程式：頁面切換
def main():
    st.sidebar.title("頁面導航")
    page = st.sidebar.selectbox("選擇頁面", ["外出統計程式", "列表頁", "統計圖"], index=0)

    if page == "外出統計程式":
        outing_stats_page()
    elif page == "列表頁":
        list_page()
    elif page == "統計圖":
        stats_chart_page()

if __name__ == "__main__":
    main()
