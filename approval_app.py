# approval_app.py (최종 완성 코드)

import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import time

# --- 설정 ---
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
CREDS_FILE = 'service_account.json'
# 중요! 본인의 Google 스프레드시트 ID를 붙여넣으세요.
SPREADSHEET_ID = '1cmpppdXcuh778qrmxq17X9McGQ3d6b7GXP2PTNQ7Ssk'

@st.cache_resource
def authorize_gspread():
    """Google Sheets API에 인증하고 클라이언트 객체를 반환합니다."""
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

st.header("📋 승인 대기 목록")

# 데이터가 비어있는 경우 처리
if df.empty or '상태' not in df.columns:
    st.success("요청 데이터가 없습니다.")
else:
    pending_requests = df[df['상태'] == '대기']

    if pending_requests.empty:
        st.success("승인 대기 중인 요청이 없습니다.")
    else:
        # Message ID를 기준으로 요청들을 그룹화합니다.
        grouped_requests = pending_requests.groupby('Message ID')

        for message_id, group_df in grouped_requests:
            # 각 그룹(배치)을 하나의 컨테이너로 묶어서 표시합니다.
            with st.container(border=True):
                
                # 그룹의 공통 정보(요청자, 요청일시)를 표시합니다.
                first_row = group_df.iloc[0]
                st.subheader(f"요청 그룹 (from: {first_row['Sender']})")
                st.caption(f"요청일시: {first_row['요청일시']}")

                # 그룹에 포함된 사용자 목록을 표로 보여줍니다.
                st.write("요청 내역:")
                st.dataframe(group_df[['이름', '1차 소속', '2차 소속', '머신 ID']], hide_index=True)

                # 그룹 전체를 한 번에 승인하는 버튼
                if st.button("✅ 이 그룹 전체 승인하기", key=f"approve_{message_id}"):
                    try:
                        # 그룹에 속한 모든 행의 인덱스를 찾습니다.
                        row_indices_to_update = group_df.index.tolist()
                        
                        update_requests = []
                        for idx in row_indices_to_update:
                            # gspread는 행 번호가 1부터 시작하고, 헤더가 1행을 차지하므로 +2를 해줍니다.
                            # G열(7번째 열)의 상태를 '승인'으로 변경
                            update_requests.append({
                                'range': f'G{idx + 2}',
                                'values': [['승인']],
                            })
                        
                        # 여러 셀을 한 번의 요청으로 업데이트하여 효율을 높입니다.
                        if update_requests:
                            sheet.batch_update(update_requests)

                        st.success(f"그룹 요청을 승인했습니다!")
                        time.sleep(1)
                        st.rerun() # 승인 후 화면을 자동으로 새로고침
                    except Exception as e:
                        st.error(f"승인 처리 중 오류 발생: {e}")