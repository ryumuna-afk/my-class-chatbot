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

# 🎨 UI 영역: 사이드바
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
# 🌟 주제별 포함 정보 및 질문 안내 (수정 완료!)
# ==========================================
if topic == "① 학교생활 적응":
    st.info(f"""
    📘 **이곳에는 이런 정보들이 들어있어요!**
    - 우리 학교의 **연간 학사 일정** 및 주요 행사
    - **창의적 체험활동(봉사, 동아리)** 관련 규정
    - **생활규정** (야간자율학습, 일과시간, 복장 등)
    
    ❓ **이렇게 물어보세요:** "축제 날짜가 언제야?", "동아리 신청은 어떻게 해?"
    """)
elif topic == "② 진로 탐색":
    st.info(f"""
    🔍 **이곳에는 이런 정보들이 들어있어요!**
    - 계열별 **추천 도서 및 권장 활동**
    - 전공/직업별 필요한 **핵심 역량** 안내
    - 우리 학교 선배들의 **진로 진학 사례** 요약
    
    ❓ **이렇게 물어보세요:** "간호학과 가려면 어떤 활동이 좋아?", "나는 만들기를 좋아하는데 직업 추천해줘."
    """)
elif topic == "③ 상급학년 준비":
    st.info(f"""
    🎯 **이곳에는 이런 정보들이 들어있어요!**
    - **2학년 선택과목** 가이드 (수능 연계 및 전공 적합성)
    - 학과별 **권장 선택 과목** 리스트
    - 상급 학년으로 올라가기 전 **체크리스트**
    
    ❓ **이렇게 물어보세요:** "공대 가려면 기하를 꼭 들어야 해?", "화학이랑 생명과학 중에 고민돼."
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

# 💬 채팅 처리 (고속 스트리밍 적용)
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
                st.error("🚨 사용량이 많습니다. 1분만 기다려주세요! (유료 티어 동기화 중일 수 있습니다.)")
            else:
                st.error(f"오류가 발생했습니다: {e}")
