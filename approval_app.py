# approval_app.py (디버깅용 최종 코드)

import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import time

# --- 설정 ---
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
CREDS_FILE = 'service_account.json'
# 중요! 본인의 Google 스프레드시트 ID를 붙여넣으세요.
SPREADSHEET_ID = '1cmpppdXcuh778qrmxq17X9McGQ3d6b7GXP2PTNQ7Ssk' # <<-- 이전에 확인한 ID

@st.cache_resource
def authorize_gspread():
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Google Sheets 인증 실패: {e}")
        st.error("Streamlit Cloud의 Secrets 설정이 올바른지 확인하세요.")
        return None

# --- UI 구성 ---
st.set_page_config(page_title="라이선스 승인", layout="centered")
st.title("👨‍💻 라이선스 발급 승인")

client = authorize_gspread()
if not client:
    st.stop()

try:
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
except Exception as e:
    st.error(f"스프레드시트 데이터 로딩 오류: {e}")
    st.stop()

if st.button("새로고침"):
    st.rerun()

# --- ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼ 디버깅 섹션 추가 ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼ ---

st.divider()
st.header("🕵️‍♂️ 디버깅 정보")

# 1. 앱이 스프레드시트에서 읽어온 원본 데이터 전체를 표시합니다.
st.subheader("1. 스프레드시트에서 읽어온 원본 데이터 (필터링 전)")
if df.empty:
    st.warning("스프레드시트에서 데이터를 읽어오지 못했거나, 시트가 비어있습니다.")
else:
    st.dataframe(df)

# 2. '상태' 열이 있는지, 데이터 타입은 무엇인지 확인합니다.
if '상태' in df.columns:
    st.info("'상태' 열을 찾았습니다.")
else:
    st.error("'상태'라는 이름의 열(Column)을 스프레드시트에서 찾을 수 없습니다. 헤더 이름을 확인해주세요!")

# 3. '대기' 상태인 데이터만 필터링한 결과를 표시합니다.
st.subheader("2. '대기' 상태로 필터링한 후의 데이터")
pending_requests = df[df['상태'] == '대기'] if '상태' in df.columns and not df.empty else pd.DataFrame()
st.dataframe(pending_requests)
st.divider()

# --- ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲ ---


st.header("📋 승인 대기 목록")

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