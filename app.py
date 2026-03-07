import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import PyPDF2
import os

# 1. 페이지 설정
st.set_page_config(page_title="꿈-잇(IT) 비서", page_icon="🤖", layout="wide")

# 2. 제미나이 AI 설정 (에러 해결: 모델 명칭 수정)
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
# 'gemini-1.5-flash' 또는 'gemini-1.5-flash-latest'가 가장 안정적입니다.
model = genai.GenerativeModel('gemini-1.5-flash') 
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. PDF 데이터 통합 로드
@st.cache_data
def load_all_pdf_data():
    combined_text = ""
    pdf_files = [f for f in os.listdir(".") if f.endswith(".pdf")]
    if not pdf_files: return "등록된 학교 자료가 없습니다."
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
    st.error("🚨 전용 링크로 접속해 주세요.")
    st.stop()

try:
    student_db = conn.read(worksheet="학생명단", ttl=600)
    matched_student = student_db[student_db['비밀코드'] == secret_code]
    student_id = str(matched_student.iloc[0]['학번'])
    student_name = matched_student.iloc[0]['이름']
except:
    st.error("인증 실패")
    st.stop()

# 🎨 사이드바 (관리자 기능만 유지)
with st.sidebar:
    st.title(f"🎓 {student_name}")
    persona = st.selectbox("🤖 비서 성격", ["다정한 친구", "꼼꼼한 비서", "냉철한 전략가"])
    topic = st.selectbox("📌 상담 주제", ["① 학교생활 적응", "② 진로 탐색", "③ 상급학년 준비"])
    st.markdown("---")
    with st.expander("🔐 관리자 (파일 업로드)"):
        if st.text_input("비밀번호", type="password") == "0486":
            file = st.file_uploader("PDF 추가", type="pdf")
            if file:
                with open(file.name, "wb") as f: f.write(file.getbuffer())
                load_all_pdf_data.clear()
                st.success("완료!")

# 🌟 메인 화면
st.title("🤖 꿈-잇(IT) 비서")

# 주제별 가이드 (데이터 요약 설명)
guides = {
    "① 학교생활 적응": "📘 **[학교생활]** 시험/축제 일정, 복장/벌점 규정, 동아리 신청 안내",
    "② 진로 탐색": "🔍 **[진로탐색]** 학과/직업 가이드, 추천 도서, 진로 설계 사례",
    "③ 상급학년 준비": "🎯 **[학업설계]** 2학년 선택과목 특징, 전공별 권장 조합"
}
st.info(guides[topic])

# 대화 기록 표시
try:
    df = conn.read(worksheet="질문기록", ttl=0).dropna(how='all')
    my_records = df[df['학번'] == student_id]
    for _, row in my_records.iterrows():
        with st.chat_message("user"): st.write(row['질문내용'])
        with st.chat_message("assistant"): st.write(row['AI답변'])
except:
    df = pd.DataFrame(columns=["날짜", "학번", "이름", "주제", "비서성격", "질문내용", "AI답변"])

# 💬 채팅 처리 (인사말 삭제, 정답만 출력)
if user_question := st.chat_input("질문을 입력하세요!"):
    with st.chat_message("user"):
        st.write(user_question)
        
    system_prompt = f"""
    [역할] 너는 학교 진로 비서야. 성격: {persona}
    [지시] 
    1. 인사는 절대 하지 마. "알겠습니다", "도와드릴게요" 같은 서론은 즉시 삭제해.
    2. [학교 데이터]에서 질문에 대한 '직접적인 정답'만 딱 말해.
    3. 데이터에 답이 있다면: 그 내용만 핵심적으로 출력해.
    4. 데이터에 답이 없다면: 반드시 "학교 자료에는 해당 내용이 없네요. 대신 일반적인 정보를 알려드릴게요."라고 먼저 말한 뒤, 네 지식으로 짧게 대답해.
    5. 질문 관련 답변만 딱 하고 끝내.

    [학교 데이터]
    {school_knowledge}
    """
    
    with st.chat_message("assistant"):
        try:
            response = model.generate_content(system_prompt, stream=True)
            
            def stream_gen():
                for chunk in response:
                    if chunk.text: yield chunk.text
            
            # 화면에 실시간 답변 출력
            full_text = st.write_stream(stream_gen())
            
            # 시트 저장
            new_row = pd.DataFrame([{
                "날짜": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "학번": student_id, "이름": student_name, "주제": topic,
                "비서성격": persona, "질문내용": user_question, "AI답변": full_text
            }])
            conn.update(worksheet="질문기록", data=pd.concat([df, new_row], ignore_index=True))
            
        except Exception as e:
            if "404" in str(e):
                st.error("🚨 모델 명칭 오류입니다. 코드를 다시 확인해 주세요.")
            elif "ResourceExhausted" in str(e):
                st.error("🚨 잠시 후 다시 시도해 주세요.")
            else:
                st.error(f"오류: {e}")
