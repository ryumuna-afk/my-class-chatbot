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
# 유료 티어 성능을 극대화하는 최신형 엔진
model = genai.GenerativeModel('gemini-2.0-flash') 
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. 모든 PDF 파일 통합 로드 함수 (캐싱)
@st.cache_data
def load_all_pdf_data():
    combined_text = ""
    all_files = os.listdir(".")
    pdf_files = [f for f in all_files if f.endswith(".pdf")]
    
    if not pdf_files:
        return "현재 학습된 학교 데이터가 없습니다."

    for file_name in pdf_files:
        try:
            with open(file_name, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                file_text = f"--- 파일명: {file_name} ---\n"
                for page in reader.pages:
                    content = page.extract_text()
                    if content:
                        file_text += content + "\n"
                combined_text += file_text + "\n"
        except Exception as e:
            combined_text += f"\n[{file_name} 읽기 오류: {e}]\n"
            
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
    if matched_student.empty:
        st.error("🚨 인증 정보가 올바르지 않습니다.")
        st.stop()
    student_id = str(matched_student.iloc[0]['학번'])
    student_name = matched_student.iloc[0]['이름']
except:
    st.error("데이터 동기화 중입니다. 잠시만 기다려 주세요.")
    st.stop()

# ==========================================
# 🎨 UI 영역: 사이드바 (가이드 추가)
# ==========================================
with st.sidebar:
    st.title("👋 반가워요!")
    st.subheader(f"{student_name} 학생, 환영합니다!")
    st.markdown("---")
    
    st.info("💡 **나의 맞춤 비서를 설정해 보세요!**\n내 고민을 가장 잘 들어줄 비서의 성격을 고를 수 있어요.")
    
    persona = st.selectbox(
        "🤖 비서의 성격을 골라주세요", 
        ["다정한 공감 친구 (응원과 격려)", "꼼꼼한 전문 비서 (정확한 정보)", "냉철한 전략가 (핵심 해결책)"]
    )
    
    st.markdown("---")
    topic = st.selectbox(
        "📌 상담받고 싶은 주제", 
        ["① 학교생활 적응", "② 진로 탐색", "③ 상급학년 준비"]
    )

    with st.expander("🔐 교사용 관리 메뉴"):
        if st.text_input("관리자 암호", type="password") == "0486":
            st.write(f"📂 **학습 파일:** {len([f for f in os.listdir('.') if f.endswith('.pdf')])}개")
            file = st.file_uploader("새 파일 추가", type="pdf")
            if file:
                with open(file.name, "wb") as f:
                    f.write(file.getbuffer())
                load_all_pdf_data.clear()
                st.success(f"'{file.name}' 추가 완료!")

# ==========================================
# 🌟 메인 화면 (주제별 요약 설명 강화)
# ==========================================
st.title("🤖 꿈-잇(IT) 비서 : 나만의 진로·학업 메이트")
st.markdown(f"##### {student_name} 학생의 질문에 핵심만 콕콕 집어 대답할게요. ✨")

# 
# 주제별 상세 자료 내용 요약 및 질문 가이드
if topic == "① 학교생활 적응":
    st.info(f"""
    📘 **[학교생활 적응] 이 방에는 이런 자료들이 들어있어요:**
    - **학사 일정:** 시험 기간, 축제, 체험학습 등 주요 날짜
    - **생활 규정:** 복장, 두발, 상·벌점 제도 및 일과 시간표
    - **활동 안내:** 봉사활동 기준, 동아리 신청 및 운영 규정
    
    ❓ **질문 예시:** "시험 범위 공지는 언제 해?", "동아리 신청 기간 알려줘."
    """)
elif topic == "② 진로 탐색":
    st.info(f"""
    🔍 **[진로 탐색] 이 방에는 이런 자료들이 들어있어요:**
    - **계열 정보:** 전공별 핵심 역량 및 권장 활동 리스트
    - **추천 도서:** 희망 직업/학과와 연계된 필독 도서 목록
    - **진로 사례:** 우리 학교 선배들의 주요 진로 설계 사례 요약
    
    ❓ **질문 예시:** "심리학과 지망생에게 추천하는 책 있어?", "마케터 활동 추천해줘."
    """)
elif topic == "③ 상급학년 준비":
    st.info(f"""
    🎯 **[상급학년 준비] 이 방에는 이런 자료들이 들어있어요:**
    - **선택과목:** 2학년 선택과목별 특징 및 수능 연계 정보
    - **학업 설계:** 학과별 권장 선택 과목 조합 가이드
    - **학점제 안내:** 수강 신청 유의사항 및 이수 기준
    
    ❓ **질문 예시:** "공대 가려면 물리II 꼭 들어야 해?", "선택과목 수강 신청 언제야?"
    """)

st.markdown("---")

# 대화 기록 표시
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

# AI 상담 및 데이터 저장
if user_question := st.chat_input("질문을 입력해 주세요!"):
    with st.chat_message("user"):
        st.write(f"**[{topic}]** {user_question}")
        
    # TMI 방지 및 핵심 답변 유도 시스템 프롬프트
    system_prompt = f"""
    너는 고등학교 1학년 학생의 다정한 진로 비서야. 성격은 '{persona}' 스타일로 대답해줘.
    [우리 학교 정보 데이터]
    {school_knowledge}
    
    [답변 약속 - 🚨핵심만 답변할 것]
    1. [핵심요약]: 질문에 대한 직접적인 결론만 '딱 1-2줄'로 가장 먼저 말해줘. (예: "OOO 선생님의 전화번호는 010-0000-0000입니다.")
    2. [자세한설명]: 추가 설명이 꼭 필요한 경우에만 아주 간결하게 덧붙여줘. 질문받지 않은 내용은 절대 먼저 말하지 마.
    3. 근거 제시: 반드시 제공된 파일 데이터에 있는 내용으로만 답변해줘.
    4. 반드시 한국어로 답변할 것.
    """
    
    with st.chat_message("assistant"):
        try:
            response = model.generate_content(system_prompt, stream=True)
            def stream_gen():
                for chunk in response:
                    if chunk.text: yield chunk.text
            full_text = st.write_stream(stream_gen())
            
            # 저장용 요약본 추출
            try:
                summary = full_text.split("[자세한설명]")[0].replace("[핵심요약]", "").strip()
            except:
                summary = full_text
            
            # 시트 업데이트
            new_row = pd.DataFrame([{
                "날짜": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "학번": student_id, "이름": student_name, "주제": topic,
                "비서성격": persona, "질문내용": user_question, "AI답변": summary
            }])
            conn.update(worksheet="질문기록", data=pd.concat([df, new_row], ignore_index=True))
            
        except Exception as e:
            st.error(f"상담 중 오류 발생: {e}")
