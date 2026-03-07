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
# 가장 빠르고 똑똑한 Flash 모델 사용
model = genai.GenerativeModel('gemini-2.5-flash') 
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. PDF 자료 초고속 암기 함수 (한 번 읽으면 캐시에 저장하여 딜레이 0초!)
@st.cache_data
def load_pdf_data():
    text = ""
    if os.path.exists("school_info.pdf"):
        with open("school_info.pdf", "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text
    else:
        return "참고할 추가 학교 자료가 없습니다."

school_knowledge = load_pdf_data()

# 4. 비밀코드(난수)로 학생 식별 및 보안 인증
secret_code = st.query_params.get("id")
if not secret_code:
    st.error("🚨 선생님이 카톡으로 보내준 '나만의 비밀 링크'로 접속해주세요!")
    st.stop()

# '학생명단' 시트에서 비밀코드 찾기
try:
    student_db = conn.read(worksheet="학생명단", ttl=600)
    matched_student = student_db[student_db['비밀코드'] == secret_code]
    
    if matched_student.empty:
        st.error("🚨 유효하지 않은 비밀코드입니다. 링크를 다시 확인해주세요.")
        st.stop()
        
    # 일치하면 학번과 이름 가져오기
    student_id = str(matched_student.iloc[0]['학번'])
    student_name = matched_student.iloc[0]['이름']
except Exception as e:
    st.error("학생 명단을 불러오는 데 실패했습니다. 선생님께 문의하세요.")
    st.stop()

# ==========================================
# 🎨 UI 영역: 사이드바 & 메인
# ==========================================
with st.sidebar:
    st.header(f"🧑‍🎓 {student_name} 학생의 방")
    st.markdown("---")
    persona = st.selectbox("🤖 나의 비서 성격은?", ["꼼꼼한 비서 (J성향)", "유쾌한 비서 (공감형)", "조언형 비서 (코칭형)"])
    topic = st.selectbox("📌 나의 관심사?", ["① 학교생활 적응", "② 진로 탐색", "③ 상급학년 준비(선택과목)"])

    # 🌟 새로 추가되는 선생님 전용 비밀 메뉴 🌟
    st.markdown("---")
    with st.expander("🔐 선생님 전용 (관리자)"):
        admin_pw = st.text_input("비밀번호 입력", type="password")
        
        # 비밀번호가 0486 일 때만 업로드 창이 열립니다! (원하시는 번호로 바꾸세요)
        if admin_pw == "0486": 
            st.success("관리자 인증 완료!")
            uploaded_file = st.file_uploader("새로운 학교 자료(PDF) 교체하기", type="pdf")
            
            if uploaded_file is not None:
                # 1. 기존 파일 덮어쓰기 (업로드한 파일 저장)
                with open("school_info.pdf", "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                # 2. AI 뇌(캐시) 강제 초기화하여 새 파일 읽게 만들기
                load_pdf_data.clear()
                st.info("✅ 자료 업데이트 완료! AI가 방금 올린 새 문서를 학습했습니다.")
        elif admin_pw:
            st.error("비밀번호가 틀렸습니다.")

st.title("🤖 My Secret-ary (나만의 진로 비서)")
st.markdown("---")

# ==========================================
# 🌟 추가된 영역: 주제별 맞춤형 질문 가이드
# ==========================================
if topic == "① 학교생활 적응":
    st.info("""
    💡 **이런 식으로 질문해 보세요!**
    - "우리 학교 봉사활동 시간은 1년에 몇 시간 채워야 해?"
    - "야간자율학습 규정이나 신청 방법 알려줘."
    - "방송부 동아리에 들어가고 싶은데 어떻게 해야 해?"
    """)
elif topic == "② 진로 탐색":
    st.info("""
    💡 **이런 식으로 질문해 보세요!**
    - "나는 사람들을 돕고 대화하는 걸 좋아하는데 어떤 직업이 어울릴까?"
    - "마케터가 되려면 고등학교 때 어떤 활동을 해두면 좋을까?"
    - "커리어넷 직업 적성 검사 결과가 '탐구형'으로 나왔는데 추천 학과 알려줘."
    """)
elif topic == "③ 상급학년 준비(선택과목)":
    st.info("""
    💡 **이런 식으로 질문해 보세요!**
    - "간호학과에 진학하고 싶은데 2학년 때 생명과학을 꼭 들어야 할까?"
    - "물리학이랑 화학 중에 뭘 선택할지 너무 고민돼. 장단점을 비교해 줘."
    - "경영학과 지망생을 위한 맞춤형 2학년 시간표를 추천해 줘."
    """)
st.markdown("---")

# ==========================================
# 💬 채팅 영역 & AI 답변 생성
# ==========================================
# '질문기록' 시트에서 과거 대화 불러오기 (데이터 증발 방지 시스템 탑재)
try:
    st.cache_data.clear() # 캐시를 강제로 한 번 더 비워줍니다.
    df = conn.read(worksheet="질문기록", usecols=list(range(7)), ttl=0)
    df = df.dropna(how='all') # 구글 시트의 쓸데없는 빈 줄을 깔끔하게 지워줍니다.
except Exception as e:
    st.error("🚨 잠시 통신 오류가 발생했습니다. (데이터 보호를 위해 저장을 차단합니다.) 새로고침(F5)을 눌러주세요!")
    st.stop() # 데이터를 완벽하게 못 읽어오면, 절대 덮어쓰지 못하도록 앱을 그 자리에서 멈춥니다!
if not df.empty:
    my_records = df[df['학번'] == student_id]
    for index, row in my_records.iterrows():
        with st.chat_message("user"):
            st.write(f"**[{row['주제']}]** {row['질문내용']}")
        with st.chat_message("assistant"):
            st.write(f"{row['AI답변']}")

# 채팅 입력 및 AI 처리
if user_question := st.chat_input("비서에게 무엇이든 물어보세요!"):
    
    # 1. 학생 질문을 화면에 띄우기
    with st.chat_message("user"):
        st.write(f"**[{topic}]** {user_question}")
        
    # 2. 제미나이 AI에게 프롬프트(명령) 내리기
    system_prompt = f"""
    너는 고등학교 1학년 학생의 진로와 학교생활을 돕는 친절한 AI 비서야.
    학생이 선택한 너의 성격은 '{persona}'야. 이 성격에 완벽하게 빙의해서 대답해줘.
    
    [우리 학교 맞춤형 자료]
    {school_knowledge}
    
    위 학교 자료를 최우선으로 참고해서, 다음 학생의 질문에 빠르고 정확하게 대답해줘. 
    자료에 없는 내용이라면 일반적인 고등학생 수준에 맞춰서 조언해줘.
    
    학생 질문: {user_question}
    """
    
    # AI 답변 생성 (스피너로 로딩 효과 주기)
    with st.chat_message("assistant"):
        with st.spinner("비서가 자료를 검토하며 답변을 작성 중입니다..."):
            response = model.generate_content(system_prompt)
            ai_answer = response.text
            st.write(ai_answer)
            
    # 3. 질문과 AI 답변을 '질문기록' 시트에 함께 저장
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_data = pd.DataFrame([{
        "날짜": now,
        "학번": student_id,
        "이름": student_name, 
        "주제": topic,
        "비서성격": persona,
        "질문내용": user_question,
        "AI답변": ai_answer
    }])
    
    updated_data = pd.concat([df, new_data], ignore_index=True)

    conn.update(worksheet="질문기록", data=updated_data)
