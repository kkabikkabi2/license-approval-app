# approval_app.py (비밀번호 기능 추가 최종 코드)

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import time

# --- ▼▼▼▼▼▼▼▼▼▼ 비밀번호 인증 함수 추가 ▼▼▼▼▼▼▼▼▼▼ ---
def check_password():
    """Secrets에 저장된 비밀번호와 일치하는지 확인하는 함수"""
    try:
        # st.secrets에서 비밀번호를 가져옵니다.
        correct_password = st.secrets["passwords"]["user1"]
    except KeyError:
        # Secrets에 비밀번호가 설정되지 않은 경우, 바로 True를 반환하여 기능을 비활성화합니다.
        return True

    # 세션 상태에 'password_correct'가 없으면 초기화
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    # 비밀번호가 아직 확인되지 않았다면, 입력창을 표시합니다.
    if not st.session_state["password_correct"]:
        st.header("🔑 비밀번호 입력")
        password = st.text_input("비밀번호를 입력하세요.", type="password")
        if st.button("로그인"):
            if password == correct_password:
                st.session_state["password_correct"] = True
                st.rerun() # 비밀번호가 맞으면 앱을 새로고침
            else:
                st.error("비밀번호가 올바르지 않습니다.")
        return False
    else:
        return True

# --- ▲▲▲▲▲▲▲▲▲▲ 비밀번호 인증 함수 끝 ▲▲▲▲▲▲▲▲▲▲ ---


# --- 설정 ---
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
SPREADSHEET_ID = '1cmpppdXcuh778qrmxq17X9McGQ3d6b7GXP2PTNQ7Ssk' 

# --- (이하 코드는 거의 동일, if check_password(): 로 감싸주는 부분만 변경) ---

st.set_page_config(page_title="라이선스 승인", layout="centered")

# ▼▼▼▼▼▼▼▼▼▼ 비밀번호 확인 절차 실행 ▼▼▼▼▼▼▼▼▼▼
if check_password():
    # --- 기존 앱 로직 시작 (인증 성공 시에만 실행) ---
    st.title("👨‍💻 라이선스 발급 승인")

    @st.cache_resource
    def authorize_gspread():
        """Google Sheets API에 인증하고 클라이언트 객체를 반환합니다."""
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
        client = gspread.authorize(creds)
        return client

    client = authorize_gspread()
    if not client:
        st.stop()
        
    # (이하 데이터 로딩 및 UI 표시는 모두 if check_password(): 블록 안에 있어야 함)
    try:
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
                    if st.button("✅ 이 그룹 전체 승인하기", key=f"approve_{message_id}"):
                        try:
                            row_indices_to_update = group_df.index.tolist()
                            update_requests = [{'range': f'G{idx + 2}', 'values': [['승인']]} for idx in row_indices_to_update]
                            if update_requests:
                                sheet.batch_update(update_requests)
                            st.success(f"그룹 요청을 승인했습니다!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"승인 처리 중 오류 발생: {e}")