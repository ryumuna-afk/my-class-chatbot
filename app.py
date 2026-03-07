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
                file_text = f"\n[자료 출처: {file_name}]\n"
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
# 🎨 UI 영역: 사이드바
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

# ==========================================
# 🌟 메인 화면 (가이드 및 챗봇)
# ==========================================
st.title("🤖 꿈-잇(IT) 비서 : 나만의 진로·학업 메이트")

# 주제별 요약 가이드 (요청하신 대로 목록화!)
if topic == "① 학교생활 적응":
    st.info("""
    📘 **[학교생활 적응] 이 방에서는 이런 걸 물어봐!**
    - **학교 생활:** 시험 일정, 축제 날짜, 학교 급식 시간
    - **지켜야 할 규칙:** 복장/두발 규정, 상벌점 제도, 휴대폰 사용 규칙
    - **우리들의 활동:** 봉사활동 채우는 법, 동아리 신청 기간
    """)
elif topic == "② 진로 탐색":
    st.info("""
    🔍 **[진로 탐색] 이 방에서는 이런 걸 물어봐!**
    - **내 꿈 찾기:** 나에게 맞는 직업과 학과 탐색
    - **생기부 관리:** 전공에 도움되는 권장 도서 및 교내 활동 추천
    """)
elif topic == "③ 상급학년 준비":
    st.info("""
    🎯 **[상급학년 준비] 이 방에서는 이런 걸 물어봐!**
    - **과목 선택:** 2학년 선택과목의 특징과 수능 연계성
    - **학업 설계:** 내가 가고 싶은 학과에 유리한 과목 추천
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

# 💬 채팅 처리
if user_question := st.chat_input("질문을 입력해 주세요!"):
    with st.chat_message("user"):
        st.write(f"**[{topic}]** {user_question}")
        
    # 🌟 [해결책] "알겠습니다"만 하지 말고 정보를 뱉으라고 명시!
    system_prompt = f"""
    너는 고등학교 진로 비서야. 성격은 '{persona}'야.
    [중요 데이터]
    {school_knowledge}
    
    [답변 원칙 - 🚨필독]
    1. 인사는 생략하고 질문에 대한 '정답'부터 말해. "알겠습니다" 같은 말은 하지 마.
    2. [핵심요약]: [중요 데이터]에서 질문과 관련된 내용을 찾아 1줄로 결론만 말해.
    3. [자세한설명]: 데이터에 근거한 구체적인 수치나 내용을 짧게 덧붙여. 데이터에 없으면 모른다고 솔직히 말해.
    4. 질문이 '전화번호'라면 반드시 데이터에서 번호를 찾아 출력해.
    """
    
    with st.chat_message("assistant"):
        try:
            response = model.generate_content(system_prompt, stream=True)
            def stream_gen():
                for chunk in response:
                    if chunk.text: yield chunk.text
            full_text = st.write_stream(stream_gen())
            
            summary = full_text.split("[자세한설명]")[0].replace("[핵심요약]", "").strip()
            
            new_row = pd.DataFrame([{
                "날짜": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "학번": student_id, "이름": student_name, "주제": topic,
                "비서성격": persona, "질문내용": user_question, "AI답변": summary
            }])
            conn.update(worksheet="질문기록", data=pd.concat([df, new_row], ignore_index=True))
        except Exception as e:
            st.error("🚨 잠시 후 다시 시도해 주세요.")
