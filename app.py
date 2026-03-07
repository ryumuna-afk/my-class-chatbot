import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import PyPDF2
import os

# 1. 페이지 및 테마 설정
st.set_page_config(
    page_title="나의 스마트 진로 비서 - 꿈-잇(IT)", 
    page_icon="🤖", 
    layout="wide"
)

# 2. 제미나이 AI 및 구글 시트 연결
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
# 유료 티어 성능을 보장하는 최신형 엔진 사용
model = genai.GenerativeModel('gemini-1.5-flash') 
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. 모든 PDF 파일 통합 로드 함수
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
                    content = page.extract_text()
                    if content:
                        combined_text += content + "\n"
        except:
            continue
    return combined_text

school_knowledge = load_all_pdf_data()

# 4. 학생 인증 (URL 파라미터 체크)
secret_code = st.query_params.get("id")
if not secret_code:
    st.error("🚨 본인의 개별 인증 링크로 접속해 주세요.")
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
    
    persona = st.selectbox(
        "🤖 비서의 성격을 골라주세요", 
        ["다정한 공감 친구", "꼼꼼한 전문 비서", "냉철한 전략가"]
    )
    
    st.markdown("---")
    topic = st.selectbox(
        "📌 상담받고 싶은 주제", 
        ["① 학교생활 적응", "② 진로 탐색", "③ 상급학년 준비"]
    )

    # 교사용 관리 메뉴 원상복구 (파일 업로드만 가능)
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

if topic == "① 학교생활 적응":
    st.info("""
    📘 **[학교생활 적응] 이 방에서는 이런 자료들을 확인할 수 있어요:**
    - 시험 일정, 축제 등 학사 일정 / 벌점 규정, 일과표 등 생활 규정 / 동아리 및 봉사활동 안내
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
# 💬 채팅 처리 (질문 관련 정답만 딱 대답하도록 강화)
# ==========================================
if user_question := st.chat_input("질문을 입력해 주세요!"):
    with st.chat_message("user"):
        st.write(f"**[{topic}]** {user_question}")
        
    # 인사는 빼고 오직 데이터에서 정답만 찾도록 지시
    system_prompt = f"""
    당신은 학교 진로 상담 AI입니다. 불필요한 인사, 수다, '알겠습니다' 같은 서론은 절대 하지 마십시오. 
    오직 아래 [학교 데이터] 내에서 질문과 가장 직접적으로 관련된 정보만 팩트 위주로 한 줄에서 두 줄 사이로 답변하십시오. 
    질문과 상관없는 주변 정보는 모두 생략하십시오. 
    데이터에 정보가 없다면 '자료에 관련 내용이 없습니다.'라고만 답하십시오.

    성격 테마: {persona}
    [학교 데이터]: {school_knowledge}
    질문: {user_question}
    """
    
    with st.chat_message("assistant"):
        try:
            # 🚀 스트리밍으로 텍스트만 출력
            response = model.generate_content(system_prompt, stream=True)
            
            def stream_gen():
                for chunk in response:
                    if chunk.text: yield chunk.text
            
            ai_answer = st.write_stream(stream_gen())
            
            # 데이터 저장
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_row = pd.DataFrame([{
                "날짜": now, "학번": student_id, "이름": student_name, 
                "주제": topic, "비서성격": persona, "질문내용": user_question, "AI답변": ai_answer
            }])
            conn.update(worksheet="질문기록", data=pd.concat([df, new_row], ignore_index=True))
            
        except Exception as e:
            if "ResourceExhausted" in str(e):
                st.error("🚨 상담 요청이 너무 많습니다. 잠시(1분) 후에 다시 시도해 주세요.")
            else:
                st.error(f"상담 중 오류가 발생했습니다: {e}")
