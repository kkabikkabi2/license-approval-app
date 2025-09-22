# approval_app.py (변경할 필요 없는 최종 코드)

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import time

def check_password():
    # ... (비밀번호 인증 로직) ...
    try:
        correct_password = st.secrets["passwords"]["user1"]
    except KeyError:
        return True
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if not st.session_state["password_correct"]:
        st.header("🔑 비밀번호 입력")
        password = st.text_input("비밀번호를 입력하세요.", type="password")
        if st.button("로그인"):
            if password == correct_password:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("비밀번호가 올바르지 않습니다.")
        return False
    else:
        return True

SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

st.set_page_config(page_title="라이선스 승인", layout="centered")

if check_password():
    st.title("👨‍💻 라이선스 발급 승인")

    @st.cache_resource
    def authorize_gspread():
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
        client = gspread.authorize(creds)
        return client

    client = authorize_gspread()
    if not client:
        st.stop()
        
    try:
        SPREADSHEET_ID = st.secrets["gcp_service_account"]["spreadsheet_id"]
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
    except Exception as e:
        st.error(f"스프레드시트 데이터 로딩 오류: {e}")
        st.stop()

    if st.button("새로고침"):
        st.rerun()

    st.header("📋 승인 대기 목록")

    if df.empty or '상태' not in df.columns:
        st.success("요청 데이터가 없습니다.")
    else:
        pending_requests = df[df['상태'] == '대기']
        if pending_requests.empty:
            st.success("승인 대기 중인 요청이 없습니다.")
        else:
            grouped_requests = pending_requests.groupby('Message ID')
            for message_id, group_df in grouped_requests:
                with st.container(border=True):
                    first_row = group_df.iloc[0]
                    st.subheader(f"요청 그룹 (from: {first_row['Sender']})")
                    st.caption(f"요청일시: {first_row['요청일시']}")
                    st.write("요청 내역:")
                    st.dataframe(group_df[['이름', '1차 소속', '2차 소속', '머신 ID']], hide_index=True)
                    
                    def update_status(new_status):
                        try:
                            row_indices_to_update = group_df.index.tolist()
                            update_requests = [{'range': f'G{idx + 2}', 'values': [[new_status]]} for idx in row_indices_to_update]
                            if update_requests:
                                sheet.batch_update(update_requests)
                            st.success(f"그룹 요청을 '{new_status}' 처리했습니다!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"처리 중 오류 발생: {e}")

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ 이 그룹 전체 승인하기", key=f"approve_{message_id}", use_container_width=True):
                            update_status("승인")
                    
                    with col2:
                        if st.button("❌ 이 그룹 전체 거절하기", key=f"reject_{message_id}", use_container_width=True):
                            update_status("반려")