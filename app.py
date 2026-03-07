import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import PyPDF2
import os

# 1. 페이지 설정
st.set_page_config(page_title="My Secret-ary", page_icon="🤖", layout="wide")

# 2. 제미나이 AI 설정 (Pro 버전 모델로 업그레이드하여 추론 오류 해결)
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
# 문맥 파악과 정보 추출 능력이 가장 뛰어난 Pro 모델 사용
model = genai.GenerativeModel('gemini-2.5-pro') 
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
# 🎨 UI 영역: 사이드바 
# ==========================================
with st.sidebar:
    st.title(f"🎓 {student_name} 학생")
    persona = st.selectbox("🤖 비서 성격", ["다정한 친구", "꼼꼼한 비서", "냉철한 전략가"])
    topic = st.selectbox("📌 상담 주제", ["① 학교생활 적응", "② 진로 탐색", "③ 상급학년 준비"])
    
    st.markdown("---")
    with st.expander("🔐 교사용 관리 메뉴"):
        if st.text_input("비밀번호 입력", type="password") == "0486":
            file = st.file_uploader("새 PDF 파일 업로드", type="pdf")
            if file:
                with open(file.name, "wb") as f: 
                    f.write(file.getbuffer())
                load_all_pdf_data.clear()
                st.success("파일 업데이트 완료!")

# ==========================================
# 🌟 메인 화면
# ==========================================
st.title("🤖 My Secret-ary (나만의 진로 비서)")

if topic == "① 학교생활 적응":
    st.info("📘 **[학교생활 적응]** 학사 일정, 생활 규정, 동아리/봉사활동 관련 정보를 물어보세요.")
elif topic == "② 진로 탐색":
    st.info("🔍 **[진로 탐색]** 직업/학과 가이드, 추천 도서, 진로 설계 사례를 물어보세요.")
elif topic == "③ 상급학년 준비":
    st.info("🎯 **[상급학년 준비]** 선택과목 특징, 전공별 권장 과목 조합을 물어보세요.")

st.markdown("---")

# 대화 기록 로드
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
# 💬 채팅 처리 (Pro 모델 전용 엄격한 프롬프트)
# ==========================================
if user_question := st.chat_input("질문을 입력하세요!"):
    with st.chat_message("user"):
        st.write(user_question)
        
    system_prompt = f"""
    당신은 고등학교 진로 상담 비서입니다. (선택된 페르소나: {persona})

    [절대 준수 규칙 - 위반 시 심각한 오류 발생]
    1. 인사말, 맺음말, 서론("네, 알려드릴게요" 등)을 절대 출력하지 마십시오. 바로 정답만 출력하십시오.
    2. 아래 [학교 데이터]를 꼼꼼히 읽고, 질문에 대한 '정확하고 직접적인 답'만 추출하십시오.
    3. 질문이 '전화번호'나 '특정 수치'를 묻는다면 데이터에서 해당 형식만 찾아 출력하고, 엉뚱한 학급 역할이나 규정을 출력하지 마십시오.
    4. [학교 데이터]에 질문에 대한 명확한 답이 없다면, 억지로 지어내거나 다른 내용을 긁어오지 말고 "제공된 학교 자료에는 해당 내용이 없습니다."라고 말한 뒤, AI의 일반 지식으로 짧게 조언하십시오.

    [학교 데이터]
    {school_knowledge}
    
    질문: {user_question}
    """
    
    with st.chat_message("assistant"):
        try:
            # 스트리밍 출력
            response = model.generate_content(system_prompt, stream=True)
            def stream_gen():
                for chunk in response:
                    if chunk.text: 
                        yield chunk.text
            full_text = st.write_stream(stream_gen())
            
            # 구글 시트 저장
            new_row = pd.DataFrame([{
                "날짜": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "학번": student_id, "이름": student_name, "주제": topic,
                "비서성격": persona, "질문내용": user_question, "AI답변": full_text
            }])
            conn.update(worksheet="질문기록", data=pd.concat([df, new_row], ignore_index=True))
            
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
