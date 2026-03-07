import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import os

# 예외 처리를 강화하여 라이브러리가 없어도 앱이 죽지 않게 함
try:
    from pypdf import PdfReader
except ImportError:
    st.error("pypdf 라이브러리를 설치 중입니다. 잠시만 기다려주세요.")

# 환경 설정
st.set_page_config(page_title="꿈-잇(IT) 비서", layout="wide")
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    st.error("설정 오류: API 키나 구글 시트 연결을 확인하세요.")

# 학교 자료 로드 (방어적 프로그래밍)
@st.cache_data
def load_data():
    text_data = ""
    for file in os.listdir("."):
        try:
            if file.endswith(".pdf"):
                reader = PdfReader(file)
                for page in reader.pages:
                    text_data += page.extract_text() + "\n"
        except: continue
    return text_data

school_knowledge = load_data()

st.title("🤖 꿈-잇(IT) 비서")

# 채팅 기억 관리
if "messages" not in st.session_state:
    st.session_state.messages = []

# 대화 출력
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
        당신은 진로 비서입니다. 
        [학교 자료]: {school_knowledge}
        [지침]: 최근 대화 맥락을 기억해. (질문 의도 파악 필수)
        [최근 대화]: {context}
        """
        
        try:
            response = model.generate_content(system_prompt)
            ai_reply = response.text
            st.markdown(ai_reply)
            st.session_state.messages.append({"role": "assistant", "content": ai_reply})
        except Exception as e:
            st.error(f"답변 생성 오류: {e}")
