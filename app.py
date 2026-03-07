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

# 3. 모든 PDF 파일 통합 로드 함수
@st.cache_data
def load_all_pdf_data():
    combined_text = ""
    pdf_files = [f for f in os.listdir(".") if f.endswith(".pdf")]
    
    if not pdf_files:
        return "현재 등록된 학교 자료가 없습니다."

    for file_name in pdf_files:
        try:
            with open(file_name, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                combined_text += f"\n--- {file_name} 내용 시작 ---\n"
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
    st.error("🚨 전용 링크로 접속해 주세요.")
    st.stop()

try:
    student_db = conn.read(worksheet="학생명단", ttl=600)
    matched_student = student_db[student_db['비밀코드'] == secret_code]
    student_id = str(matched_student.iloc[0]['학번'])
    student_name = matched_student.iloc[0]['이름']
except:
    st.error("인증 정보를 불러오지 못했습니다.")
    st.stop()

# ==========================================
# 🎨 UI 영역: 사이드바 (관리자 메뉴 간소화)
# ==========================================
with st.sidebar:
    st.title("👋 반가워요!")
    st.subheader(f"{student_name} 학생!")
    st.markdown("---")
    
    persona = st.selectbox(
        "🤖 비서 성격", 
        ["다정한 공감 친구", "꼼꼼한 전문 비서", "냉철한 전략가"]
    )
    
    topic = st.selectbox(
        "📌 상담 주제", 
        ["① 학교생활 적응", "② 진로 탐색", "③ 상급학년 준비"]
    )

    st.markdown("---")
    with st.expander("🔐 관리자 전용"):
        if st.text_input("PW", type="password") == "0486":
            file = st.file_uploader("PDF 추가", type="pdf")
            if file:
                with open(file.name, "wb") as f:
                    f.write(file.getbuffer())
                load_all_pdf_data.clear()
                st.success("업로드 완료!")

# ==========================================
# 🌟 메인 화면 (주제별 요약 안내)
# ==========================================
st.title("🤖 꿈-잇(IT) 비서 : 나만의 진로·학업 메이트")

if topic == "① 학교생활 적응":
    st.info("📘 **[학교생활 적응]** 학사 일정, 생활 규정(복장/상벌점), 동아리 및 봉사활동 안내")
elif topic == "② 진로 탐색":
    st.info("🔍 **[진로 탐색]** 희망 직업/학과 역량 가이드, 추천 도서, 진로 설계 사례")
elif topic == "③ 상급학년 준비":
    st.info("🎯 **[상급학년 준비]** 2학년 선택과목 특징, 학과별 권장 조합, 수강 신청 방법")

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
            st.write(row['AI답변'])
except:
    df = pd.DataFrame(columns=["날짜", "학번", "이름", "주제", "비서성격", "질문내용", "AI답변"])

# ==========================================
# 💬 채팅 처리 (데이터 우선 순위 및 지식 결합)
# ==========================================
if user_question := st.chat_input("질문을 입력하세요!"):
    with st.chat_message("user"):
        st.write(f"**[{topic}]** {user_question}")
        
    # 핵심 지침: 데이터에 없으면 '없음'을 알리고 제미나이 지식으로 답변
    system_prompt = f"""
    너는 고등학교 진로 비서야. 성격은 '{persona}' 스타일로 답변해.
    
    [규칙]
    1. 인사는 절대 하지 마. (예: "안녕하세요", "알겠습니다" 등 금지)
    2. [학교 데이터]에서 질문에 대한 답을 먼저 찾아.
    3. 만약 [학교 데이터]에 답이 있다면, 그 내용만 핵심적으로 딱 말해.
    4. 만약 [학교 데이터]에 답이 없다면, 반드시 "학교 자료에는 해당 내용이 없어서 일반적인 정보를 알려드릴게요."라고 먼저 말한 뒤, 네 지식을 바탕으로 아주 짧고 유익하게 답변해.
    5. 질문 관련 답변만 딱 하고 끝내.
    
    [학교 데이터]
    {school_knowledge}
    """
    
    with st.chat_message("assistant"):
        try:
            response = model.generate_content(system_prompt, stream=True)
            
            def stream_gen():
                for chunk in response:
                    if chunk.text: yield chunk.text
            
            full_text = st.write_stream(stream_gen())
            
            # 시트 저장
            new_row = pd.DataFrame([{
                "날짜": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "학번": student_id, "이름": student_name, "주제": topic,
                "비서성격": persona, "질문내용": user_question, "AI답변": full_text
            }])
            conn.update(worksheet="질문기록", data=pd.concat([df, new_row], ignore_index=True))
            
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
