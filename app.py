import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import os
from pypdf import PdfReader  # 🌟 이제 requirements.txt에 pypdf가 있으니 문제없습니다.
from PIL import Image

# 1. 환경 설정
st.set_page_config(page_title="꿈-잇(IT) 비서", layout="wide")
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.0-flash') 
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 학교 자료 로드
@st.cache_data
def load_global_files():
    file_parts = []
    # PDF, 엑셀, 이미지 모두 지원
    for file_name in os.listdir("."):
        try:
            if file_name.lower().endswith(".pdf"):
                reader = PdfReader(file_name)
                text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
                file_parts.append(f"--- [학교 PDF: {file_name}] ---\n{text}")
            elif file_name.lower().endswith((".xlsx", ".xls", ".csv")):
                df = pd.read_csv(file_name) if file_name.endswith(".csv") else pd.read_excel(file_name)
                file_parts.append(f"--- [학교 엑셀: {file_name}] ---\n{df.to_csv(index=False)}")
            elif file_name.lower().endswith((".png", ".jpg", ".jpeg")):
                file_parts.append(f"--- [이미지 파일: {file_name}] ---")
        except: continue
    return "\n\n".join(file_parts)

school_knowledge = load_global_files()

# 3. 인증 로직
secret_code = st.query_params.get("id")
if not secret_code: st.stop()
student_db = conn.read(worksheet="학생명단", ttl=600)
matched = student_db[student_db['비밀코드'] == secret_code]
if matched.empty: st.stop()
student_name = matched.iloc[0]['이름']

# 4. 채팅 기억 관리
if "messages" not in st.session_state: st.session_state.messages = []

st.title(f"🤖 {student_name} 학생의 꿈-잇(IT) 비서")
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

# 5. 질문 처리
if prompt := st.chat_input("질문을 입력하세요!"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        # 이전 대화 3개 문맥 포함
        context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-4:]])
        
        system_prompt = f"""
        당신은 학교 진로 상담 비서입니다.
        [학교 자료]: {school_knowledge}
        [최근 대화 맥락]: {context}
        
        [지시사항]
        1. 최근 대화를 참고하여 학생의 질문 의도를 파악해(예: '1학년' 질문이 나오면 이전 주제인 '중간고사'와 연결해).
        2. 학교 자료에서 답을 찾고, 친절하게 설명해.
        3. 답이 없으면 선생님께 확인하라고 해.
        """
        response = model.generate_content(system_prompt)
        ai_reply = response.text
        st.markdown(ai_reply)
        st.session_state.messages.append({"role": "assistant", "content": ai_reply})
