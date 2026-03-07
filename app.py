import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import os
import PyPDF2
from PIL import Image

# 1. 설정
st.set_page_config(page_title="꿈-잇(IT) 비서", layout="wide")
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.0-flash') 
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 데이터 로드 (PyPDF2로 통일)
@st.cache_data
def load_data():
    data_list = []
    # 폴더 내 모든 파일 스캔
    for file in os.listdir("."):
        if file.endswith(".pdf"):
            with open(file, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
                data_list.append(f"--- [PDF 자료: {file}] ---\n{text}")
        elif file.lower().endswith((".xlsx", ".xls", ".csv")):
            df = pd.read_csv(file) if file.endswith(".csv") else pd.read_excel(file)
            data_list.append(f"--- [엑셀 자료: {file}] ---\n{df.to_csv(index=False)}")
        elif file.lower().endswith((".png", ".jpg", ".jpeg")):
            data_list.append(f"--- [이미지 자료: {file}] ---")
    return "\n\n".join(data_list)

school_knowledge = load_data()

# 3. UI 및 인증
st.title("🤖 꿈-잇(IT) 비서")
# 인증 로직 (기존 유지)
# ... (생략) ...

# 4. 대화 기억하기 (Session State 활용)
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. 질문 처리 (문맥 우선순위 강화)
if prompt := st.chat_input("질문을 입력하세요!"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # 최근 대화 내용을 요약하여 문맥으로 전달
        context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-4:]])
        
        system_prompt = f"""
        당신은 고등학교 진로 비서입니다.
        [학교 자료]: {school_knowledge}
        
        [행동 수칙 - 매우 중요]
        1. 【최근 대화】를 먼저 확인해. 만약 학생이 '1학년'처럼 짧게 물었다면, 직전 대화의 맥락(예: 중간고사)을 이어받아 '1학년 중간고사'에 대한 정보를 학교 자료에서 찾아야 해.
        2. 학교 자료에 정보가 있으면 정확히 말하고, 없으면 아는 지식으로 조언하되 학교에 확인하라고 해.
        3. 엉뚱한 등교 시간 같은 정보를 먼저 뱉지 마. 의도를 파악해.
        
        [최근 대화]: {context}
        """
        
        response = model.generate_content(system_prompt)
        ai_reply = response.text
        st.markdown(ai_reply)
        st.session_state.messages.append({"role": "assistant", "content": ai_reply})
