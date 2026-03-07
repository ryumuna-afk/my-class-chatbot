import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import PyPDF2
import os

# 1. 페이지 설정
st.set_page_config(
    page_title="나의 스마트 진로 비서 - 꿈-잇(IT)", 
    page_icon="🤖", 
    layout="wide"
)

# 2. 제미나이 AI 및 구글 시트 연결
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.0-flash') 
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. 모든 PDF 통합 로드 함수
@st.cache_data
def load_all_pdf_data():
    combined_text = ""
    pdf_files = [f for f in os.listdir(".") if f.endswith(".pdf")]
    
    if not pdf_files:
        return "현재 학습된 학교 데이터가 없습니다."

    for file_name in pdf_files:
        try:
            with open(file_name, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                combined_text += f"\n--- {file_name} 자료 시작 ---\n"
                for page in reader.pages:
                    combined_text += page.extract_text() + "\n"
        except:
            continue
    return combined_text

school_knowledge = load_all_pdf_data()

# 4. 학생 인증 (비밀코드)
secret_code = st.query_params.get("id")
if not secret_code:
    st.error("🚨 선생님이 보내주신 '나만의 비밀 링크'로 접속해 주세요!")
    st.stop()

try:
    student_db = conn.read(worksheet="학생명단", ttl=600)
    matched_student = student_db[student_db['비밀코드'] == secret_code]
    student_id = str(matched_student.iloc[0]['학번'])
    student_name = matched_student.iloc[0]['이름']
except:
    st.error("인증 오류가 발생했습니다.")
    st.stop()

# ==========================================
# 🎨 UI 영역: 사이드바 (관리자 메뉴 간소화)
# ==========================================
with st.sidebar:
    st.title("👋 반가워요!")
    st.subheader(f"{student_name} 학생, 환영합니다!")
    st.markdown("---")
    
    st.info("💡 **나의 맞춤 비서를 설정해 보세요!**")
    
    persona = st.selectbox(
        "🤖 비서의 성격을 골라주세요", 
        ["다정한 공감 친구 (응원과 격려)", "꼼꼼한 전문 비서 (정확한 정보)", "냉철한 전략가 (핵심 해결책)"]
    )
    
    st.markdown("---")
    topic = st.selectbox(
        "📌 상담받고 싶은 주제", 
        ["① 학교생활 적응", "② 진로 탐색", "③ 상급학년 준비"]
    )

    # 🌟 관리자 메뉴 원상복구 (파일 업로드만 가능)
    st.markdown("---")
    with st.expander("🔐 교사용 관리 메뉴"):
        if st.text_input("관리자 암호", type="password") == "0486":
            file = st.file_uploader("새로운 학교 자료(PDF) 추가하기", type="pdf")
            if file:
                with open(file.name, "wb") as f:
                    f.write(file.getbuffer())
                load_all_pdf_data.clear()
                st.success(f"'{file.name}' 자료가 추가되었습니다!")

# ==========================================
# 🌟 메인 화면 (주제별 요약 설명)
# ==========================================
st.title("🤖 꿈-잇(IT) 비서 : 나만의 진로·학업 메이트")
st.markdown(f"##### {student_name} 학생, 무엇을 도와줄까요? ✨")

if topic == "① 학교생활 적응":
    st.info("""
    📘 **[학교생활 적응] 이 방에서는 이런 자료들을 확인할 수 있어요:**
    - 시험 기간, 축제 등 학사 일정 / 벌점 규정, 일과표 등 생활 규정 / 동아리 및 봉사활동 안내
    """)
elif topic == "② 진로 탐색":
    st.info("""
    🔍 **[진로 탐색] 이 방에서는 이런 자료들을 확인할 수 있어요:**
    - 희망 직업/학과별 역량 가이드 / 권장 도서 리스트 / 진로 설계 사례 요약
    """)
elif topic == "③ 상급학년 준비":
    st.info("""
    🎯 **[상급학년 준비] 이 방에서는 이런 자료들을 확인할 수 있어요:**
    - 2학년 선택과목별 특징 및 수능 연계 / 학과별 권장 과목 조합 / 수강 신청 방법
    """)

st.markdown("---")

# 대화 기록 로드
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
    df = pd.DataFrame(columns=["날짜", "학번", "이름", "주제", "비서성격", "질문내용", "AI답변"])

# ==========================================
# 💬 채팅 처리 (질문 관련 내용만 답변하도록 강화)
# ==========================================
if user_question := st.chat_input("비서에게 무엇이든 물어보세요!"):
    with st.chat_message("user"):
        st.write(f"**[{topic}]** {user_question}")
        
    # 🌟 질문과 관계없는 내용은 절대 말하지 않도록 강력한 페널티 부여
    system_prompt = f"""
    너는 고등학교 진로 비서야. 성격은 '{persona}' 스타일로 답변해줘.
    [우리 학교 데이터] {school_knowledge}
    
    [답변 원칙 - 🚨매우 중요]
    1. 반드시 질문받은 내용에 대해서만 답변해. 질문과 상관없는 다른 데이터 내용은 절대 언급하지 마.
    2. [핵심요약]: 질문에 대한 직접적인 결론만 딱 1-2줄로 대답해. (예: 번호를 물으면 번호만, 날짜를 물으면 날짜만)
    3. [자세한설명]: 질문에 대한 구체적인 근거가 자료에 있는 경우에만 아주 짧게 덧붙여줘.
    4. 질문 내용이 자료에 없으면 엉뚱한 정보를 주지 말고 "죄송합니다. 해당 정보는 제가 가지고 있는 자료에 없네요."라고 정중히 답해줘.
    """
    
    with st.chat_message("assistant"):
        try:
            response = model.generate_content(system_prompt, stream=True)
            
            def stream_gen():
                for chunk in response:
                    if chunk.text: yield chunk.text
            
            full_text = st.write_stream(stream_gen())
            
            # 시트 저장용 요약본 추출
            try:
                summary = full_text.split("[자세한설명]")[0].replace("[핵심요약]", "").strip()
            except:
                summary = full_text
            
            # 데이터 저장
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_row = pd.DataFrame([{
                "날짜": now, "학번": student_id, "이름": student_name, 
                "주제": topic, "비서성격": persona, "질문내용": user_question, "AI답변": summary
            }])
            conn.update(worksheet="질문기록", data=pd.concat([df, new_row], ignore_index=True))
            
        except Exception as e:
            st.error(f"상담 중 오류 발생: {e}")
