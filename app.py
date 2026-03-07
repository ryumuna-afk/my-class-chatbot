import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import PyPDF2
import os
import time

# 1. 페이지 설정
st.set_page_config(page_title="My Secret-ary", page_icon="🤖", layout="wide")

# 2. 제미나이 AI 및 구글 시트 연결
# gemini-1.5-flash가 가장 안정적입니다. (최신 버전 이름 주의)
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash') 
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. PDF 자료 로드 함수
@st.cache_data
def load_pdf_data():
    text = ""
    if os.path.exists("school_info.pdf"):
        with open("school_info.pdf", "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text
    return "학교 자료가 없습니다."

school_knowledge = load_pdf_data()

# 4. 학생 인증
secret_code = st.query_params.get("id")
if not secret_code:
    st.error("🚨 올바른 링크로 접속해주세요!")
    st.stop()

try:
    student_db = conn.read(worksheet="학생명단", ttl=600)
    matched_student = student_db[student_db['비밀코드'] == secret_code]
    if matched_student.empty:
        st.error("🚨 유효하지 않은 비밀코드입니다.")
        st.stop()
    student_id = str(matched_student.iloc[0]['학번'])
    student_name = matched_student.iloc[0]['이름']
except Exception:
    st.error("서버 연결 오류입니다. 잠시 후 다시 시도하세요.")
    st.stop()

# 🎨 UI
with st.sidebar:
    st.header(f"🧑‍🎓 {student_name} 학생의 방")
    persona = st.selectbox("🤖 비서 성격", ["꼼꼼한 비서", "유쾌한 비서", "조언형 비서"])
    topic = st.selectbox("📌 관심사", ["① 학교생활 적응", "② 진로 탐색", "③ 상급학년 준비"])

    st.markdown("---")
    with st.expander("🔐 관리자 모드"):
        if st.text_input("비밀번호", type="password") == "0486":
            uploaded_file = st.file_uploader("PDF 업로드", type="pdf")
            if uploaded_file:
                with open("school_info.pdf", "wb") as f:
                    f.write(uploaded_file.getbuffer())
                load_pdf_data.clear()
                st.info("✅ 업데이트 완료!")

st.title("🤖 My Secret-ary")
st.markdown("---")

# 채팅 내역 로드
try:
    df = conn.read(worksheet="질문기록", ttl=0)
    df = df.dropna(how='all')
    my_records = df[df['학번'] == student_id]
    for _, row in my_records.iterrows():
        with st.chat_message("user"):
            st.write(f"**[{row['주제']}]** {row['질문내용']}")
        with st.chat_message("assistant"):
            st.write(f"{row['AI답변']}")
except:
    pass

# 채팅 처리
if user_question := st.chat_input("질문을 입력하세요!"):
    with st.chat_message("user"):
        st.write(f"**[{topic}]** {user_question}")
        
    system_prompt = f"""
    너는 친절한 학교 진로 비서야. 성격: {persona}
    [학교 자료] {school_knowledge}
    
    [답변 규칙]
    1. [핵심요약] 태그로 핵심을 1줄 요약해줘.
    2. [자세한설명] 태그로 상세히 설명해줘.
    학생 질문: {user_question}
    """
    
    with st.chat_message("assistant"):
        # 답변 생성 및 에러 처리 (ResourceExhausted 대응)
        try:
            response = model.generate_content(system_prompt, stream=True)
            
            # 제너레이터로 답변 스트리밍
            def stream_gen():
                for chunk in response:
                    yield chunk.text
            
            ai_answer = st.write_stream(stream_gen())
            
            # 요약 저장 로직
            summary = ai_answer.split("[자세한설명]")[0].replace("[핵심요약]", "").strip()
            
            # 시트 저장
            new_row = pd.DataFrame([{
                "날짜": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "학번": student_id, "이름": student_name, "주제": topic,
                "비서성격": persona, "질문내용": user_question, "AI답변": summary
            }])
            conn.update(worksheet="질문기록", data=pd.concat([df, new_row], ignore_index=True))
            
        except Exception as e:
            if "ResourceExhausted" in str(e):
                st.error("🚨 너무 많이 질문했어요! 잠시(1분 정도) 기다렸다가 다시 질문해주세요.")
            else:
                st.error("오류 발생: " + str(e))
