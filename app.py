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
# 유료 티어의 성능을 100% 발휘하는 최신형 엔진
model = genai.GenerativeModel('gemini-2.0-flash') 
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. PDF 자료 로드 함수 (캐싱 적용)
@st.cache_data
def load_pdf_data():
    text = ""
    if os.path.exists("school_info.pdf"):
        with open("school_info.pdf", "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text
    return "참고할 학교 자료가 없습니다."

school_knowledge = load_pdf_data()

# 4. 학생 인증 (비밀코드 체크)
secret_code = st.query_params.get("id")
if not secret_code:
    st.error("🚨 선생님이 카톡으로 보내준 '비밀 링크'로 접속해주세요!")
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
    st.error("학생 명단을 불러오는 중 오류가 발생했습니다.")
    st.stop()

# ==========================================
# 🎨 UI 영역: 사이드바
# ==========================================
with st.sidebar:
    st.header(f"🧑‍🎓 {student_name} 학생의 방")
    st.markdown("---")
    persona = st.selectbox("🤖 나의 비서 성격은?", ["꼼꼼한 비서 (J성향)", "유쾌한 비서 (공감형)", "조언형 비서 (코칭형)"])
    topic = st.selectbox("📌 나의 관심사?", ["① 학교생활 적응", "② 진로 탐색", "③ 상급학년 준비"])

    st.markdown("---")
    with st.expander("🔐 선생님 전용 (관리자)"):
        admin_pw = st.text_input("비밀번호", type="password")
        if admin_pw == "0486": 
            st.success("관리자 인증 성공!")
            uploaded_file = st.file_uploader("새 PDF 교체하기", type="pdf")
            if uploaded_file:
                with open("school_info.pdf", "wb") as f:
                    f.write(uploaded_file.getbuffer())
                load_pdf_data.clear()
                st.info("✅ 자료가 교체되었습니다. 새로고침(F5) 하세요.")
        elif admin_pw:
            st.error("비밀번호가 틀렸습니다.")

st.title("🤖 My Secret-ary (나만의 진로 비서)")

# ==========================================
# 🌟 주제별 포함 정보 목록 및 질문 안내
# ==========================================
if topic == "① 학교생활 적응":
    st.info(f"""
    📘 **[학교생활 적응] 이 방에서 알 수 있는 정보:**
    - **연간 학사 일정:** 시험 기간, 축제, 체험학습 날짜 등
    - **창체 활동:** 자율/봉사/동아리 활동 규정 및 신청 방법
    - **학교 생활규정:** 일과 시간표, 복장 및 두발 규정, 상벌점 제도
    - **시설 이용:** 도서관, 자습실 이용 시간 및 방법
    
    ❓ **질문 예시:** "시험 범위 공지는 보통 언제 해?", "동아리 기수제 규정이 어떻게 돼?"
    """)
elif topic == "② 진로 탐색":
    st.info(f"""
    🔍 **[진로 탐색] 이 방에서 알 수 있는 정보:**
    - **계열별 정보:** 인문/사회/자연/공학 등 계열별 특징
    - **추천 활동:** 희망 진로와 관련된 독서 목록 및 교내 대회
    - **핵심 역량:** 특정 직업/학과에서 중요하게 보는 성격과 능력
    - **선배들의 사례:** 졸업생들의 주요 진로 선택 흐름 요약
    
    ❓ **질문 예시:** "경찰이 되고 싶은데 추천하는 동아리 있어?", "의료 계열 권장 도서 알려줘."
    """)
elif topic == "③ 상급학년 준비":
    st.info(f"""
    🎯 **[상급학년 준비] 이 방에서 알 수 있는 정보:**
    - **선택과목 가이드:** 2학년 때 배우는 과목들의 특징과 수능 연계성
    - **전공 적합성:** 내가 가고 싶은 학과에 유리한 선택과목 리스트
    - **학점제 안내:** 고교학점제 운영 방식 및 수강 신청 유의사항
    - **학년별 로드맵:** 1학년 겨울방학 때 준비해야 할 필수 항목
    
    ❓ **질문 예시:** "미디어학과 지망생인데 미적분을 꼭 들어야 해?", "사탐 과목 중에 뭐가 제일 인기 많아?"
    """)

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
    df = pd.DataFrame(columns=["날짜", "학번", "이름", "주제", "비서성격", "질문내용", "AI답변"])

# 💬 채팅 처리 (유료 티어 고속 스트리밍 적용)
if user_question := st.chat_input("비서에게 무엇이든 물어보세요!"):
    with st.chat_message("user"):
        st.write(f"**[{topic}]** {user_question}")
        
    system_prompt = f"""
    너는 고등학교 1학년 진로 비서야. 성격: {persona}
    [참고자료] {school_knowledge}
    
    [답변 규칙]
    - [핵심요약] 태그로 핵심을 1~2줄 요약.
    - [자세한설명] 태그로 친절한 설명.
    질문: {user_question}
    """
    
    with st.chat_message("assistant"):
        try:
            response = model.generate_content(system_prompt, stream=True)
            
            # 실시간 타자 효과 생성
            def stream_gen():
                for chunk in response:
                    if chunk.text:
                        yield chunk.text
            
            full_response_text = st.write_stream(stream_gen())
            
            # 요약본 추출 로직
            try:
                summary_to_save = full_response_text.split("[자세한설명]")[0].replace("[핵심요약]", "").strip()
            except:
                summary_to_save = full_response_text
            
            # 데이터 저장
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_row = pd.DataFrame([{
                "날짜": now, "학번": student_id, "이름": student_name, 
                "주제": topic, "비서성격": persona, "질문내용": user_question, "AI답변": summary_to_save
            }])
            
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(worksheet="질문기록", data=updated_df)
            
        except Exception as e:
            if "ResourceExhausted" in str(e):
                st.error("🚨 사용량이 많습니다. 1분만 기다려주세요! (유료 티어 반영 중일 수 있습니다.)")
            else:
                st.error(f"오류가 발생했습니다: {e}")
