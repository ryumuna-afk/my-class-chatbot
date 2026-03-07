import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import PyPDF2
import os

# 1. 페이지 설정
st.set_page_config(page_title="꿈-잇(IT) 비서", page_icon="🤖", layout="wide")

# 2. 제미나이 AI 설정
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.0-flash') 
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. 모든 PDF 데이터 로드
@st.cache_data
def load_all_pdf_data():
    combined_text = ""
    pdf_files = [f for f in os.listdir(".") if f.endswith(".pdf")]
    if not pdf_files: 
        return "데이터 없음"
    
    for file_name in pdf_files:
        try:
            with open(file_name, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    combined_text += page.extract_text() + "\n"
        except: 
            continue
    return combined_text

school_knowledge = load_all_pdf_data()

# 4. 학생 인증
secret_code = st.query_params.get("id")
if not secret_code:
    st.error("🚨 올바른 전용 링크로 접속해 주세요.")
    st.stop()

try:
    student_db = conn.read(worksheet="학생명단", ttl=600)
    matched_student = student_db[student_db['비밀코드'] == secret_code]
    student_id = str(matched_student.iloc[0]['학번'])
    student_name = matched_student.iloc[0]['이름']
except:
    st.error("서버 연결에 실패했습니다. (학생 명단 확인 불가)")
    st.stop()

# ==========================================
# 🎨 UI 영역 1: 사이드바 (관리자 전용 & 동기화 버튼 추가)
# ==========================================
with st.sidebar:
    st.markdown("### 🔐 교사용 관리 메뉴")
    if st.text_input("비밀번호 입력", type="password") == "0486":
        
        # 🌟 [신규 추가] 깃허브 업로드 시 수동 동기화 버튼
        if st.button("🔄 깃허브 데이터 동기화 (캐시 초기화)"):
            load_all_pdf_data.clear() # 기존 기억 삭제
            st.success("데이터 동기화 완료! 이제 새 파일을 인식합니다.")
            st.rerun() # 화면 새로고침
            
        st.markdown("---")
        file = st.file_uploader("새 PDF 파일 업로드 (앱에서 직접)", type="pdf")
        if file:
            with open(file.name, "wb") as f: 
                f.write(file.getbuffer())
            load_all_pdf_data.clear()
            st.success("파일 업데이트 완료!")

# ==========================================
# 🌟 UI 영역 2: 메인 화면
# ==========================================
st.markdown("### 🤖 꿈-잇(IT) 비서 : 나만의 진로·학업 메이트")
st.markdown(f"**반가워요, {student_name} 학생! 환영합니다 🎓**")
st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    persona = st.selectbox("🤖 비서 성격", ["다정한 친구", "꼼꼼한 비서", "냉철한 전략가"])
with col2:
    topic = st.selectbox("📌 상담 주제", ["① 학교생활 적응", "② 진로 탐색", "③ 상급학년 준비"])

if topic == "① 학교생활 적응":
    st.info("📘 **[학교생활 적응]** 학사 일정, 생활 규정, 동아리/봉사활동 관련 정보를 물어보세요.")
elif topic == "② 진로 탐색":
    st.info("🔍 **[진로 탐색]** 직업/학과 가이드, 추천 도서, 진로 설계 사례를 물어보세요.")
elif topic == "③ 상급학년 준비":
    st.info("🎯 **[상급학년 준비]** 선택과목 특징, 전공별 권장 과목 조합을 물어보세요.")

st.markdown("---")

try:
    df = conn.read(worksheet="질문기록", ttl=0).dropna(how='all')
    my_records = df[df['학번'] == student_id]
    for _, row in my_records.iterrows():
        with st.chat_message("user"): 
            st.write(row['질문내용'])
        with st.chat_message("assistant"): 
            st.write(row['AI답변'])
except:
    df = pd.DataFrame(columns=["날짜", "학번", "이름", "주제", "비서성격", "질문내용", "AI답변"])

# ==========================================
# 💬 채팅 처리
# ==========================================
if user_question := st.chat_input("질문을 입력하세요!"):
    with st.chat_message("user"):
        st.write(user_question)
        
    system_prompt = f"""
    당신은 고등학교 진로 상담 비서입니다. (선택된 페르소나: {persona})

    [답변 가이드라인]
    1. 아래 [학교 데이터]를 읽고 질문에 대한 '정확하고 직접적인 답'을 최우선으로 찾으십시오.
    2. 데이터에서 정답을 찾았다면, 선택된 페르소나의 말투에 어울리는 '자연스러운 한두 문장'으로 짧고 명확하게 대답하십시오.
    3. 서론이나 엉뚱한 정보(TMI)는 절대 추가하지 마십시오.
    4. 🚨중요🚨: [학교 데이터]에 질문에 대한 명확한 답이 없다면, AI의 일반 지식을 바탕으로 유익한 답변을 제공하십시오. 단, 답변 마지막에 반드시 "이는 일반적인 내용이므로, 정확한 내용은 학교나 선생님께 꼭 다시 확인해 봐!"라는 취지의 안내 멘트를 페르소나 말투에 맞게 자연스럽게 덧붙이십시오.

    [학교 데이터]
    {school_knowledge}
    
    질문: {user_question}
    """
    
    with st.chat_message("assistant"):
        try:
            response = model.generate_content(system_prompt, stream=True)
            def stream_gen():
                for chunk in response:
                    if chunk.text: 
                        yield chunk.text
            full_text = st.write_stream(stream_gen())
            
            new_row = pd.DataFrame([{
                "날짜": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "학번": student_id, "이름": student_name, "주제": topic,
                "비서성격": persona, "질문내용": user_question, "AI답변": full_text
            }])
            conn.update(worksheet="질문기록", data=pd.concat([df, new_row], ignore_index=True))
            
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
