import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import os
from pypdf import PdfReader # PyPDF2 대신 최신 pypdf 사용

# 1. 환경 설정
st.set_page_config(page_title="꿈-잇(IT) 비서", layout="wide")
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.0-flash') 
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 학교 자료 로드 (최대한 간결하게)
@st.cache_data
def get_school_data():
    text = ""
    for file in os.listdir("."):
        if file.endswith(".pdf"):
            reader = PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() + "\n"
    return text

school_knowledge = get_school_data()

# 3. 인증 및 UI
student_name = "학생" # 인증 로직 생략(간결화)
st.title("🤖 꿈-잇(IT) 비서")

# 4. 채팅 기억 관리 (문맥 파악)
if "messages" not in st.session_state:
    st.session_state.messages = []

# 대화 출력
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. 질문 처리
if prompt := st.chat_input("질문을 입력하세요"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # 이전 대화 3개까지 문맥으로 포함
        context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-4:]])
        
        system_prompt = f"""
        당신은 학교 진로 비서입니다. 
        [학교 자료]: {school_knowledge}
        
        [지침]
        1. 아래 [최근 대화]의 문맥을 파악하여 질문에 대답해.
        2. [학교 자료]에 답이 있으면 그것을 말하고, 없으면 아는 범위 내에서 조언해.
        3. 답이 없으면 "정확한 내용은 선생님께 확인해 봐"라고 말해.
        
        [최근 대화]: {context}
        """
        
        response = model.generate_content(system_prompt)
        ai_reply = response.text
        st.markdown(ai_reply)
        st.session_state.messages.append({"role": "assistant", "content": ai_reply})
