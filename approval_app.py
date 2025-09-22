# approval_app.py (최신 인증 라이브러리 적용 최종 코드)

import streamlit as st
import gspread
import pandas as pd
import time
# ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼ 새로운 인증 라이브러리를 import 합니다 ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
from google.oauth2.service_account import Credentials
# ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

# --- 설정 ---
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
# SPREADSHEET_ID는 Streamlit의 Secrets에서 직접 가져옵니다.

@st.cache_resource
def authorize_gspread():
    """Google Sheets API에 인증하고 클라이언트 객체를 반환합니다."""
    try:
        creds_dict = st.secrets["gcp_service_account"]
        
        # ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼ 인증 코드를 최신 방식으로 수정 ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
        client = gspread.authorize(creds)
        # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
        
        return client
    except Exception as e:
        st.error(f"Google Sheets 인증 실패: {e}")
        st.error("Streamlit Cloud의 Secrets 설정이 올바른지 확인하세요.")
        return None

# --- UI 구성 (이하 로직은 변경 없음) ---
st.set_page_config(page_title="라이선스 승인", layout="centered")
st.title("👨‍💻 라이선스 발급 승인")

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