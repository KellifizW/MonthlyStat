# 測試頁
def test_page():
    st.title("測試頁：本區/外區判斷")
    st.write("請上傳 CSV 檔案，程式將根據 GitHub 的 homelist.csv 判斷每筆資料是否屬於本區（使用 Big5HKSCS 編碼）。")
    uploaded_file = st.file_uploader("選擇 CSV 檔案", type=["csv"], key="test_uploader")

    if uploaded_file is not None:
        # 讀取上傳的 CSV
        st.write("檔案已上傳，名稱:", uploaded_file.name)
        uploaded_df, used_encoding = read_csv_with_big5(uploaded_file)
        if uploaded_df is None:
            return

        st.write(f"檔案成功解析，使用編碼: {used_encoding}")
        st.write("上傳檔案的前幾行數據：")
        st.dataframe(uploaded_df.head())

        # 讀取 GitHub 的 homelist.csv
        github_df = get_github_csv_data(RAW_URL)
        if github_df is None:
            return

        # 檢查必要的欄位是否存在
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

        # 提取 HomeName 的前 3 個數字並判斷區域
        def extract_home_number(home_name):
            if pd.isna(home_name):
                return None
            # 提取前 3 個數字
            import re
            match = re.match(r'^\d{1,3}', str(home_name))
            return match.group(0) if match else None

        def check_local(row, github_df):
            home_number = extract_home_number(row['HomeName'])
            resp_staff = row['RespStaff'] if pd.notna(row['RespStaff']) else None
            second_staff = row['2ndRespStaffName'] if pd.notna(row['2ndRespStaffName']) else None

            if home_number is None:
                return '外區'  # 如果無法提取數字，默認為外區

            # 在 github_df 中查找匹配 Home 的記錄
            matching_homes = github_df[github_df['Home'].astype(str) == str(home_number)]
            if matching_homes.empty:
                return '外區'  # 如果沒有匹配的 Home，視為外區

            # 提取匹配 Home 的 staff1 和 staff2
            local_staff = set()
            for _, home_row in matching_homes.iterrows():
                if pd.notna(home_row['staff1']):
                    local_staff.add(home_row['staff1'])
                if pd.notna(home_row['staff2']):
                    local_staff.add(home_row['staff2'])

            # 判斷是否本區
            if (resp_staff in local_staff) or (second_staff in local_staff):
                return '本區'
            return '外區'

        # 應用判斷邏輯
        uploaded_df['區域'] = uploaded_df.apply(lambda row: check_local(row, github_df), axis=1)

        # 顯示結果
        st.subheader("判斷結果")
        st.dataframe(uploaded_df)

        # 統計本區與外區數量
        region_counts = uploaded_df['區域'].value_counts()
        st.subheader("區域統計")
        st.write(f"本區記錄數: {region_counts.get('本區', 0)}")
        st.write(f"外區記錄數: {region_counts.get('外區', 0)}")
