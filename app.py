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
# 가장 안정적이고 빠른 최신 모델 사용
model = genai.GenerativeModel('gemini-2.0-flash') 
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. PDF 자료 초고속 암기 함수
@st.cache_data
def load_pdf_data():
    text = ""
    if os.path.exists("school_info.pdf"):
        with open("school_info.pdf", "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text
    else:
        return "참고할 추가 학교 자료가 없습니다."

school_knowledge = load_pdf_data()

# 4. 비밀코드(난수)로 학생 식별 및 보안 인증
secret_code = st.query_params.get("id")
if not secret_code:
    st.error("🚨 선생님이 카톡으로 보내준 '나만의 비밀 링크'로 접속해주세요!")
    st.stop()

try:
    student_db = conn.read(worksheet="학생명단", ttl=600)
    matched_student = student_db[student_db['비밀코드'] == secret_code]
    
    if matched_student.empty:
        st.error("🚨 유효하지 않은 비밀코드입니다. 링크를 다시 확인해주세요.")
        st.stop()
        
    student_id = str(matched_student.iloc[0]['학번'])
    student_name = matched_student.iloc[0]['이름']
except Exception:
    st.error("학생 명단을 불러오는 데 실패했습니다.")
    st.stop()

# ==========================================
# 🎨 UI 영역: 사이드바 & 메인
# ==========================================
with st.sidebar:
    st.header(f"🧑‍🎓 {student_name} 학생의 방")
    st.markdown("---")
    persona = st.selectbox("🤖 나의 비서 성격은?", ["꼼꼼한 비서 (J성향)", "유쾌한 비서 (공감형)", "조언형 비서 (코칭형)"])
    topic = st.selectbox("📌 나의 관심사?", ["① 학교생활 적응", "② 진로 탐색", "③ 상급학년 준비(선택과목)"])

    st.markdown("---")
    with st.expander("🔐 선생님 전용 (관리자)"):
        admin_pw = st.text_input("비밀번호 입력", type="password")
        if admin_pw == "0486": 
            uploaded_file = st.file_uploader("새로운 학교 자료(PDF) 교체하기", type="pdf")
            if uploaded_file is not None:
                with open("school_info.pdf", "wb") as f:
                    f.write(uploaded_file.getbuffer())
                load_pdf_data.clear()
                st.info("✅ 자료 업데이트 완료!")
        elif admin_pw:
            st.error("비밀번호가 틀렸습니다.")

st.title("🤖 My Secret-ary (나만의 진로 비서)")
# 주제별 질문 가이드
if topic == "① 학교생활 적응":
    st.info("💡 질문 예시: '우리 학교 봉사활동 시간은 어떻게 채워?', '야간자율학습 신청은 어떻게 해?'")
elif topic == "② 진로 탐색":
    st.info("💡 질문 예시: '내 성격에 맞는 직업 추천해 줘.', '마케터가 되려면 어떤 활동을 해야 해?'")
elif topic == "③ 상급학년 준비(선택과목)":
    st.info("💡 질문 예시: '간호학과 가려면 생명과학을 꼭 들어야 할까?', '2학년 선택과목 고민돼. 추천해 줘.'")

st.markdown("---")

# ==========================================
# 💬 채팅 영역 & AI 답변 생성
# ==========================================
try:
    df = conn.read(worksheet="질문기록", usecols=list(range(7)), ttl=0)
    df = df.dropna(how='all') 
except Exception:
    df = pd.DataFrame(columns=["날짜", "학번", "이름", "주제", "비서성격", "질문내용", "AI답변"])

if not df.empty:
    my_records = df[df['학번'] == student_id]
    for _, row in my_records.iterrows():
        with st.chat_message("user"):
            st.write(f"**[{row['주제']}]** {row['질문내용']}")
        with st.chat_message("assistant"):
            st.write(f"{row['AI답변']}")

if user_question := st.chat_input("비서에게 무엇이든 물어보세요!"):
    with st.chat_message("user"):
        st.write(f"**[{topic}]** {user_question}")
        
    system_prompt = f"""
    너는 고등학교 1학년 학생의 진로와 학교생활을 돕는 친절한 AI 비서야.
    성격: {persona}, 학생 질문: {user_question}
    [자료] {school_knowledge}
    [답변 규칙]
    [핵심요약] (1~2줄 요약)
    [자세한설명] (구체적인 설명)
    """
    
    with st.chat_message("assistant"):
        # 답변 스트리밍 생성 (Generator 함수 활용)
        response = model.generate_content(system_prompt, stream=True)
        def stream_gen():
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        
        ai_answer = st.write_stream(stream_gen())
            
    # 시트 저장
    try:
        summary_for_sheet = ai_answer.split("[자세한설명]")[0].replace("[핵심요약]", "").strip()
    except:
        summary_for_sheet = ai_answer
        
    new_data = pd.DataFrame([{
        "날짜": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "학번": student_id,
        "이름": student_name, 
        "주제": topic,
        "비서성격": persona,
        "질문내용": user_question,
        "AI답변": summary_for_sheet
    }])
    
    updated_data = pd.concat([df, new_data], ignore_index=True)
    conn.update(worksheet="질문기록", data=updated_data)


