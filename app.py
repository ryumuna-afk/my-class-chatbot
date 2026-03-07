import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import PyPDF2
import os
from PIL import Image # 🌟 이미지 처리 도구 추가

# ==========================================
# 1. 페이지 및 기본 환경 설정
# ==========================================
st.set_page_config(page_title="My Secret-ary", page_icon="🤖", layout="wide")

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')
conn = st.connection("gsheets", type=GSheetsConnection)

# ==========================================
# 2. PDF 자료 초고속 암기
# ==========================================
@st.cache_data
def load_pdf_data():
    text = ""
    if os.path.exists("school_info.pdf"):
        try:
            with open("school_info.pdf", "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
            return text
        except Exception as e:
            return "PDF 파일을 읽는 중 오류가 발생했습니다."
    else:
        return "참고할 추가 학교 자료가 없습니다. 일반적인 지식으로 답변합니다."

school_knowledge = load_pdf_data()

# ==========================================
# 3. 비밀코드(난수)로 학생 식별 및 보안 인증
# ==========================================
secret_code = st.query_params.get("id")

if not secret_code:
    st.error("🚨 선생님이 카톡으로 보내준 '나만의 비밀 링크'로 접속해주세요! (예: /?id=x7k9p)")
    st.stop()

try:
    student_db = conn.read(worksheet="학생명단", ttl=600)
    matched_student = student_db[student_db['비밀코드'] == secret_code]
    
    if matched_student.empty:
        st.error("🚨 유효하지 않은 비밀코드입니다. 링크를 다시 확인해주세요.")
        st.stop()
        
    student_id = str(matched_student.iloc[0]['학번'])
    student_name = matched_student.iloc[0]['이름']
except Exception as e:
    st.error("학생 명단을 불러오는 데 실패했습니다.")
    st.stop()

# ==========================================
# 4. 🎨 UI 영역: 왼쪽 사이드바 (🌟 이미지 첨부 추가)
# ==========================================
with st.sidebar:
    st.header(f"🧑‍🎓 {student_name} 학생의 방")
    st.markdown("---")
    persona = st.selectbox("🤖 나의 비서 성격은?", ["꼼꼼한 비서 (J성향)", "유쾌한 비서 (공감형)", "조언형 비서 (코칭형)"])
    topic = st.selectbox("📌 나의 관심사?", ["① 학교생활 적응", "② 진로 탐색", "③ 상급학년 준비(선택과목)"])
    
    # 🌟 이미지 업로드 위젯 추가
    st.markdown("---")
    st.subheader("📎 이미지 첨부 (선택)")
    uploaded_image = st.file_uploader("진로 검사지, 시간표 등을 올려주세요!", type=["png", "jpg", "jpeg"])
    if uploaded_image:
        st.success("사진이 첨부되었습니다! 아래에 질문을 입력하세요.")

st.title("🤖 My Secret-ary (나만의 진로 비서)")
st.markdown("---")

col1, col2, col3 = st.columns(3)
with col1:
    with st.expander("🏫 1. 슬기로운 고1 생활"):
        st.write("✅ 교내 동아리 목록\n✅ 봉사활동 안내\n✅ 야간자율학습 규정")
with col2:
    with st.expander("🧭 2. 나를 찾는 진로 탐색"):
        st.write("✅ 커리어넷 직업 검사\n✅ 나의 롤모델 찾기\n✅ 학과 정보 검색")
with col3:
    with st.expander("📚 3. 고교학점제 과목 설계"):
        st.write("✅ 전공별 권장 과목\n✅ 공동교육과정 안내\n✅ 2학년 시간표 가설계")

st.markdown("---")
st.subheader("💬 비서와 대화하기")

# ==========================================
# 5. 💬 과거 채팅 기록 불러오기
# ==========================================
try:
    df = conn.read(worksheet="질문기록", usecols=list(range(7)), ttl=0)
except Exception:
    df = pd.DataFrame(columns=["날짜", "학번", "이름", "주제", "비서성격", "질문내용", "AI답변"])

if not df.empty:
    my_records = df[df['학번'] == student_id]
    for index, row in my_records.iterrows():
        with st.chat_message("user"):
            st.write(f"**[{row['주제']}]** {row['질문내용']}")
        with st.chat_message("assistant"):
            st.write(f"{row['AI답변']}")

# ==========================================
# 6. 🚀 새로운 질문 입력 및 눈 달린 AI 답변 생성
# ==========================================
if user_question := st.chat_input("비서에게 무엇이든 물어보세요!"):
    
    # 구글 시트에 저장할 때 이미지 첨부 여부 표시
    display_question = f"[사진 첨부됨] 📸 {user_question}" if uploaded_image else user_question

    with st.chat_message("user"):
        st.write(f"**[{topic}]** {display_question}")
        
    system_prompt = f"""
    너는 고등학교 1학년 학생의 진로와 학교생활을 돕는 전용 AI 비서야.
    학생이 선택한 너의 성격은 '{persona}'야. 이 성격에 맞게 친절하게 대화하듯 대답해.
    
    [우리 학교 맞춤형 자료]
    {school_knowledge}
    
    【답변 규칙】
    1. 학생의 질문이 '학교생활', '진로탐색', '상급학년 준비'와 관련이 있다면, 학교 자료와 너의 지식을 바탕으로 친절하게 답변해.
    2. 🚨 관련 없는 엉뚱한 질문(요리, 연예인, 게임 등)이라면 절대 답하지 말고 단호하게 거절해. ("진로 전용 비서라서 대답할 수 없어!")
    3. 만약 학생이 '이미지(사진)'를 함께 첨부했다면, 그 이미지를 꼼꼼히 분석해서 질문에 알맞게 대답해줘.
    """
    
    with st.chat_message("assistant"):
        with st.spinner("비서가 질문(과 사진)을 분석하며 답변을 작성 중입니다..."):
            try:
                # 🌟 제미나이에게 보낼 준비물 상자 (프롬프트 + 질문)
                prompt_parts = [system_prompt]
                
                # 🌟 사진이 업로드 되었다면 준비물 상자에 사진도 같이 넣기!
                if uploaded_image:
                    img = Image.open(uploaded_image)
                    prompt_parts.append(img)
                
                # 마지막으로 학생 질문 넣기
                prompt_parts.append(f"\n학생 질문: {user_question}")
                
                # 제미나이에게 상자 통째로 전달하기
                response = model.generate_content(prompt_parts)
                ai_answer = response.text
                st.write(ai_answer)
                
            except Exception as e:
                ai_answer = f"앗, 비서의 두뇌에 잠시 오류가 생겼어요. 잠시 후 다시 시도해주세요! (오류내용: {e})"
                st.write(ai_answer)
            
    # 구글 시트에 저장
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_data = pd.DataFrame([{
        "날짜": now,
        "학번": student_id,
        "이름": student_name, 
        "주제": topic,
        "비서성격": persona,
        "질문내용": display_question, # 사진 첨부 여부가 포함된 질문 내용
        "AI답변": ai_answer
    }])
    
    updated_data = pd.concat([df, new_data], ignore_index=True)
    conn.update(worksheet="질문기록", data=updated_data)
