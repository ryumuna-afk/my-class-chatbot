import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import PyPDF2
import os

# 1. 페이지 설정 (브라우저 탭에 표시될 이름)
st.set_page_config(
    page_title="나의 스마트 진로 비서 - 꿈-잇(IT)", 
    page_icon="🤖", 
    layout="wide"
)

# 2. 제미나이 AI 및 구글 시트 연결
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.0-flash') 
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. 데이터 로드 함수
@st.cache_data
def load_pdf_data():
    text = ""
    if os.path.exists("school_info.pdf"):
        with open("school_info.pdf", "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text
    return "현재 학습된 학교 데이터가 없습니다."

school_knowledge = load_pdf_data()

# 4. 학생 인증
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
    st.error("데이터를 불러오는 중입니다. 잠시만 기다려 주세요.")
    st.stop()

# ==========================================
# 🎨 UI 영역: 사이드바 (친절한 가이드 추가)
# ==========================================
with st.sidebar:
    st.title("👋 반가워요!")
    st.subheader(f"{student_name} 학생, 환영합니다!")
    st.markdown("---")
    
    # 🌟 비서 성향 선택 안내 멘트
    st.info("💡 **나의 맞춤 비서를 설정해 보세요!**\n고민을 들어줄 친구가 필요한지, 정확한 분석이 필요한지에 따라 비서의 성격을 고를 수 있어요.")
    
    persona = st.selectbox(
        "🤖 비서의 성격을 골라주세요", 
        ["다정한 공감 친구 (응원과 격려)", "꼼꼼한 전문 비서 (정확한 정보)", "냉철한 전략가 (핵심 해결책)"]
    )
    
    st.markdown("---")
    topic = st.selectbox(
        "📌 상담받고 싶은 주제", 
        ["① 학교생활 적응", "② 진로 탐색", "③ 상급학년 준비"]
    )

    # 교사용 메뉴 (비밀번호는 유지)
    st.markdown("---")
    with st.expander("🔐 교사용 관리 메뉴"):
        if st.text_input("관리자 암호", type="password") == "0486":
            file = st.file_uploader("학교 PDF 업데이트", type="pdf")
            if file:
                with open("school_info.pdf", "wb") as f:
                    f.write(file.getbuffer())
                load_pdf_data.clear()
                st.success("자료 업데이트 완료!")

# ==========================================
# 🌟 메인 화면 (친근한 제목으로 변경)
# ==========================================
# 
st.title("🤖 꿈-잇(IT) 비서 : 나만의 진로·학업 메이트")
st.markdown(f"##### {student_name} 학생의 꿈을 위해 AI 비서가 함께 고민할게요. ✨")

# 주제별 상세 정보 안내 (리스트화)
if topic == "① 학교생활 적응":
    st.info(f"""
    📘 **[학교생활 적응] 이 방에서는 이런 걸 도와줄게!**
    - **학교의 모든 것:** 시험 일정, 학교 축제, 등교 시간표
    - **우리들의 약속:** 벌점 규정, 교복 입는 법, 자습실 이용 규칙
    - **즐거운 활동:** 동아리 종류와 신청법, 봉사활동 시간 채우기
    
    ❓ **질문 예시:** "우리 학교 동아리 신청 언제까지야?", "벌점 지우는 방법 알려줘!"
    """)
elif topic == "② 진로 탐색":
    st.info(f"""
    🔍 **[진로 탐색] 이 방에서는 이런 걸 도와줄게!**
    - **내 꿈 찾기:** 나에게 어울리는 직업과 학과 추천
    - **생기부 채우기:** 전공에 도움되는 권장 도서와 교내 활동
    - **역량 기르기:** 특정 직업을 갖기 위해 지금 해야 할 일들
    
    ❓ **질문 예시:** "경찰이 꿈인데 어떤 책을 읽으면 좋아?", "나에게 맞는 전공은 뭘까?"
    """)
elif topic == "③ 상급학년 준비":
    st.info(f"""
    🎯 **[상급학년 준비] 이 방에서는 이런 걸 도와줄게!**
    - **과목 선택하기:** 2학년 때 배우는 과목들의 특징(물리, 경제 등)
    - **나만의 시간표:** 내가 가고 싶은 학과에 유리한 과목 추천
    - **학점제 미리보기:** 수강 신청 방법과 유의해야 할 점
    
    ❓ **질문 예시:** "간호학과 가려면 화학 꼭 들어야 해?", "미적분은 언제 배우는 거야?"
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
if user_question := st.chat_input("AI 비서에게 무엇이든 물어보세요!"):
    with st.chat_message("user"):
        st.write(f"**[{topic}]** {user_question}")
        
    system_prompt = f"""
    너는 고등학교 1학년 학생의 다정한 진로 비서야. 성격은 '{persona}' 스타일로 대답해줘.
    [우리 학교 정보] {school_knowledge}
    
    [답변 약속]
    1. [핵심요약]: 가장 중요한 답변을 맨 처음에 1-2줄로 짧게 요약해줘.
    2. [자세한설명]: 친절하고 구체적으로 설명해줘.
    3. 반드시 한국어로, 학생의 눈높이에서 대답해줘.
    """
    
    with st.chat_message("assistant"):
        try:
            response = model.generate_content(system_prompt, stream=True)
            
            def stream_gen():
                for chunk in response:
                    if chunk.text:
                        yield chunk.text
            
            full_text = st.write_stream(stream_gen())
            
            # 시트 저장용 요약본 추출
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
            if "ResourceExhausted" in str(e):
                st.error("🚨 지금은 상담 예약이 꽉 찼어요! 1분만 기다렸다가 다시 말을 걸어줄래?")
            else:
                st.error(f"앗, 상담 중에 잠깐 문제가 생겼어: {e}")
