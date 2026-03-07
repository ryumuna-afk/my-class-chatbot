import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import PyPDF2
import os

# 1. 페이지 설정
st.set_page_config(page_title="꿈-잇(IT) 비서", page_icon="🤖", layout="wide")

# 2. 제미나이 AI 설정 (2.0 엔진 고정)
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.0-flash') 
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. PDF 데이터 로드
@st.cache_data
def load_all_pdf_data():
    combined_text = ""
    pdf_files = [f for f in os.listdir(".") if f.endswith(".pdf")]
    if not pdf_files: return "데이터 없음"
    for file_name in pdf_files:
        try:
            with open(file_name, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    combined_text += page.extract_text() + "\n"
        except: continue
    return combined_text

school_knowledge = load_all_pdf_data()

# 4. 학생 인증
secret_code = st.query_params.get("id")
if not secret_code:
    st.error("🚨 인증 링크로 접속하세요.")
    st.stop()

try:
    student_db = conn.read(worksheet="학생명단", ttl=600)
    matched_student = student_db[student_db['비밀코드'] == secret_code]
    student_id = str(matched_student.iloc[0]['학번'])
    student_name = matched_student.iloc[0]['이름']
except:
    st.error("인증 실패")
    st.stop()

# 🎨 사이드바
with st.sidebar:
    st.title(f"🎓 {student_name}")
    persona = st.selectbox("🤖 비서 성격", ["다정한 친구", "꼼꼼한 비서", "냉철한 전략가"])
    topic = st.selectbox("📌 상담 주제", ["① 학교생활 적응", "② 진로 탐색", "③ 상급학년 준비"])
    
    st.markdown("---")
    with st.expander("🔐 관리자 (파일 업로드)"):
        if st.text_input("PW", type="password") == "0486":
            file = st.file_uploader("PDF 추가", type="pdf")
            if file:
                with open(file.name, "wb") as f: f.write(file.getbuffer())
                load_all_pdf_data.clear()
                st.success("완료")

# 🌟 메인 화면
st.title("🤖 꿈-잇(IT) 비서")

if topic == "① 학교생활 적응":
    st.info("📘 학사 일정, 생활 규정, 동아리/봉사활동 안내")
elif topic == "② 진로 탐색":
    st.info("🔍 직업/학과 가이드, 추천 도서, 진로 사례")
elif topic == "③ 상급학년 준비":
    st.info("🎯 선택과목 특징, 전공별 권장 조합")

st.markdown("---")

# 대화 기록
try:
    df = conn.read(worksheet="질문기록", ttl=0).dropna(how='all')
    my_records = df[df['학번'] == student_id]
    for _, row in my_records.iterrows():
        with st.chat_message("user"): st.write(row['질문내용'])
        with st.chat_message("assistant"): st.write(row['AI답변'])
except:
    df = pd.DataFrame(columns=["날짜", "학번", "이름", "주제", "비서성격", "질문내용", "AI답변"])

# 💬 채팅 처리 (인사 생략, 핵심 답변 전용)
if user_question := st.chat_input("질문을 입력하세요!"):
    with st.chat_message("user"):
        st.write(user_question)
        
    system_prompt = f"""
    [역할] 학교 진로 비서. 성격: {persona}
    [지시] 
    1. 인사는 절대 하지 마. (예: "안녕하세요", "알겠습니다" 등 금지)
    2. [학교 데이터]에서 질문에 대한 답을 찾아 핵심만 말해.
    3. 데이터에 답이 없으면 "자료에 해당 내용이 없네요."라고 말하고 네 지식으로 짧게 대답해.
    4. 질문 관련 답변만 하고 끝내.

    [학교 데이터]
    {school_knowledge}
    """
    
    with st.chat_message("assistant"):
        try:
            response = model.generate_content(system_prompt, stream=True)
            def stream_gen():
                for chunk in response:
                    if chunk.text: yield chunk.text
            full_text = st.write_stream(stream_gen())
            
            # 저장
            new_row = pd.DataFrame([{
                "날짜": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "학번": student_id, "이름": student_name, "주제": topic,
                "비서성격": persona, "질문내용": user_question, "AI답변": full_text
            }])
            conn.update(worksheet="질문기록", data=pd.concat([df, new_row], ignore_index=True))
        except Exception as e:
            st.error(f"오류: {e}")
