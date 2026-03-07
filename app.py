import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import PyPDF2
import os

# 1. 페이지 설정
st.set_page_config(page_title="My Secret-ary", page_icon="🤖", layout="wide")

# 2. 제미나이 AI 및 구글 시트 연결
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
    return "참고할 추가 학교 자료가 없습니다."

school_knowledge = load_pdf_data()

# 4. 학생 인증 (비밀코드)
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
    st.error("학생 명단을 불러오는 데 실패했습니다.")
    st.stop()

# 🎨 UI 영역: 사이드바
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
                st.info("✅ 업데이트 완료! 새로고침(F5) 하세요.")

# 메인 UI
st.title("🤖 My Secret-ary")

# 주제별 질문 가이드 (복구 완료!)
if topic == "① 학교생활 적응":
    st.info("💡 질문 예시: '우리 학교 봉사활동 시간은 1년에 몇 시간 채워야 해?', '야간자율학습 신청은 어떻게 해?'")
elif topic == "② 진로 탐색":
    st.info("💡 질문 예시: '나에게 맞는 직업을 추천해 줘.', '마케터가 되려면 고등학교 때 무엇을 하면 좋을까?'")
elif topic == "③ 상급학년 준비":
    st.info("💡 질문 예시: '간호학과 진학을 위해 생명과학을 선택해야 할까?', '경영학과를 위한 2학년 시간표 추천해 줘.'")

st.markdown("---")

# 💬 채팅 내역 로드
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
    - [핵심요약] 태그로 핵심을 1줄 요약해줘.
    - [자세한설명] 태그로 상세히 설명해줘.
    학생 질문: {user_question}
    """
    
    with st.chat_message("assistant"):
        try:
            response = model.generate_content(system_prompt, stream=True)
            
            # 스트리밍 방식 답변 출력
            def stream_gen():
                for chunk in response:
                    if chunk.text:
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
            st.error("🚨 오류 발생: 잠시 후 다시 시도해주세요.")
