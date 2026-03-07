import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import os
import PyPDF2  # PyPDF2로 다시 변경했습니다.
from PIL import Image

# 환경 설정
st.set_page_config(page_title="꿈-잇(IT) 비서", layout="wide")
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')
conn = st.connection("gsheets", type=GSheetsConnection)

# 학교 자료 로드 (기본 기능만)
@st.cache_data
def load_data():
    text_data = ""
    for file in os.listdir("."):
        if file.endswith(".pdf"):
            with open(file, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text_data += page.extract_text() + "\n"
    return text_data

school_knowledge = load_data()

st.title("🤖 꿈-잇(IT) 비서 (기본 복구 버전)")

# 채팅 기억 관리
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 질문 처리
if prompt := st.chat_input("질문을 입력하세요"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-4:]])
        system_prompt = f"""
        당신은 학교 진로 비서입니다.
        [학교 자료]: {school_knowledge}
        [지침]: 최근 대화 맥락을 파악하여 질문에 답해줘. 답이 없으면 선생님께 확인하라고 해.
        [최근 대화]: {context}
        """
        response = model.generate_content(system_prompt)
        ai_reply = response.text
        st.markdown(ai_reply)
        st.session_state.messages.append({"role": "assistant", "content": ai_reply})
