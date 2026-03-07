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
# 유료 티어 성능을 보장하는 2.0 모델
model = genai.GenerativeModel('gemini-2.0-flash') 
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
                combined_text += f"\n--- 파일 시작: {file_name} ---\n"
                for page in reader.pages:
                    content = page.extract_text()
                    if content:
                        combined_text += content + "\n"
        except:
            continue
    return combined_text

school_knowledge = load_all_pdf_data()

# 4. 학생 인증
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
    st.error("학생 정보를 불러오지 못했습니다.")
    st.stop()

# ==========================================
# 🎨 UI 영역: 사이드바
# ==========================================
with st.sidebar:
    st.title("👋 반가워요!")
    st.subheader(f"{student_name} 학생, 환영합니다!")
    st.markdown("---")
    
    persona = st.selectbox(
        "🤖 비서의 성격을 골라주세요", 
        ["다정한 공감 친구 (응원과 격려)", "꼼꼼한 전문 비서 (정확한 정보)", "냉철한 전략가 (핵심 해결책)"]
    )
    
    st.markdown("---")
    topic = st.selectbox(
        "📌 상담받고 싶은 주제", 
        ["① 학교생활 적응", "② 진로 탐색", "③ 상급학년 준비"]
    )

    with st.expander("🔐 관리자 시스템 (진단용)"):
        if st.text_input("Access PW", type="password") == "0486":
            st.write(f"📂 **학습된 텍스트 길이:** {len(school_knowledge)}자")
            # 🌟 [진단] 실제 읽어온 텍스트가 있는지 미리보기 (선생님만 확인용)
            if st.checkbox("학습된 내용 요약 보기"):
                st.text(school_knowledge[:500] + "...") 
            
            file = st.file_uploader("새 PDF 추가", type="pdf")
            if file:
                with open(file.name, "wb") as f:
                    f.write(file.getbuffer())
                load_all_pdf_data.clear()
                st.success("데이터 업데이트 완료!")

# ==========================================
# 🌟 메인 화면 (가이드 보강)
# ==========================================
st.title("🤖 꿈-잇(IT) 비서 : 나만의 진로·학업 메이트")

if topic == "① 학교생활 적응":
    st.info("""
    📘 **[학교생활 적응] 이 방에서는 이런 걸 물어봐!**
    - **학교의 지도:** 시험 기간, 축제 날짜, 일과표(급식/하교 시간)
    - **생활 규칙:** 복장 규정, 상벌점 제도, 휴대폰 규정, 담임 선생님 번호
    - **우리들의 활동:** 동아리 신청 기간, 봉사활동 기준
    """)
elif topic == "② 진로 탐색":
    st.info("""
    🔍 **[진로 탐색] 이 방에서는 이런 걸 물어봐!**
    - **내 꿈 찾기:** 나에게 맞는 학과 추천 및 직업 탐색
    - **생기부 관리:** 전공별 권장 도서 리스트 및 교내 활동 제안
    """)
elif topic == "③ 상급학년 준비":
    st.info("""
    🎯 **[상급학년 준비] 이 방에서는 이런 걸 물어봐!**
    - **과목 선택:** 2학년 선택과목별 수능 연계 및 특징
    - **학업 설계:** 전공에 유리한 과목 조합 및 수강 신청 안내
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

# 💬 채팅 처리 (초강력 입단속 프롬프트)
if user_question := st.chat_input("질문을 입력하세요!"):
    with st.chat_message("user"):
        st.write(f"**[{topic}]** {user_question}")
        
    # 🌟 [개선] 서론 금지, 데이터 우선 검색 지시
    system_prompt = f"""
    너는 고등학교 진로 비서야. 성격은 '{persona}'야.
    
    [명령 - 🚨최우선 순위]
    1. 인사는 절대 하지 마. "알겠습니다", "도와드릴게요" 같은 서론을 즉시 삭제해.
    2. [핵심요약]: 아래 제공된 [참고자료]에서 질문에 대한 '구체적인 정답(수치, 전화번호, 날짜 등)'만 딱 1줄로 말해.
    3. [자세한설명]: 정답에 대한 근거만 짧게 말해. 자료에 없는 내용은 절대 지어내지 말고 "자료에 없습니다"라고 해.
    4. 질문이 전화번호를 묻는다면, 자료를 샅샅이 뒤져서 숫자 형태의 번호를 출력해.
    
    [참고자료]
    {school_knowledge}
    """
    
    with st.chat_message("assistant"):
        try:
            response = model.generate_content(system_prompt, stream=True)
            def stream_gen():
                for chunk in response:
                    if chunk.text: yield chunk.text
            full_text = st.write_stream(stream_gen())
            
            # 저장용 요약본
            try:
                summary = full_text.split("[자세한설명]")[0].replace("[핵심요약]", "").strip()
            except:
                summary = full_text
            
            # 시트 저장
            new_row = pd.DataFrame([{
                "날짜": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "학번": student_id, "이름": student_name, "주제": topic,
                "비서성격": persona, "질문내용": user_question, "AI답변": summary
            }])
            conn.update(worksheet="질문기록", data=pd.concat([df, new_row], ignore_index=True))
        except Exception as e:
            st.error(f"상담 중 오류: {e}")
