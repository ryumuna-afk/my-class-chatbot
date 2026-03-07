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

# 3. 🌟 [업그레이드] 모든 PDF 파일을 읽어오는 함수
@st.cache_data
def load_all_pdf_data():
    combined_text = ""
    # 현재 폴더 내의 모든 파일을 리스트업
    all_files = os.listdir(".")
    # 그 중 .pdf로 끝나는 파일만 골라내기
    pdf_files = [f for f in all_files if f.endswith(".pdf")]
    
    if not pdf_files:
        return "현재 학습된 학교 데이터가 없습니다."

    for file_name in pdf_files:
        try:
            with open(file_name, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                file_text = f"--- 파일명: {file_name} ---\n"
                for page in reader.pages:
                    content = page.extract_text()
                    if content:
                        file_text += content + "\n"
                combined_text += file_text + "\n"
        except Exception as e:
            combined_text += f"\n[{file_name} 읽기 오류: {e}]\n"
            
    return combined_text

# 모든 데이터 로드
school_knowledge = load_all_pdf_data()

# 4. 학생 인증 (비밀코드)
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

    # 교사용 관리 메뉴
    st.markdown("---")
    with st.expander("🔐 교사용 관리 메뉴"):
        if st.text_input("관리자 암호", type="password") == "0486":
            st.write(f"📂 **현재 학습된 파일:** {len([f for f in os.listdir('.') if f.endswith('.pdf')])}개")
            file = st.file_uploader("새 파일 추가하기", type="pdf")
            if file:
                # 업로드한 파일 이름 그대로 저장
                with open(file.name, "wb") as f:
                    f.write(file.getbuffer())
                load_all_pdf_data.clear()
                st.success(f"'{file.name}' 추가 완료!")

# ==========================================
# 🌟 메인 화면
# ==========================================
st.title("🤖 꿈-잇(IT) 비서 : 나만의 진로·학업 메이트")
st.markdown(f"##### {student_name} 학생의 꿈을 위해 AI 비서가 함께 고민할게요. ✨")

# 주제별 가이드
if topic == "① 학교생활 적응":
    st.info("📘 **[학교생활 적응]** 학사 일정, 생활 규정, 동아리 활동 등 학교생활 전반을 도와줄게!")
elif topic == "② 진로 탐색":
    st.info("🔍 **[진로 탐색]** 나에게 맞는 직업, 학과 추천부터 생기부 활동까지 함께 고민해 보자!")
elif topic == "③ 상급학년 준비":
    st.info("🎯 **[상급학년 준비]** 선택과목 가이드와 나만의 시간표 설계로 다음 학년을 준비하자!")

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

# AI 상담 및 데이터 저장
if user_question := st.chat_input("AI 비서에게 무엇이든 물어보세요!"):
    with st.chat_message("user"):
        st.write(f"**[{topic}]** {user_question}")
        
    system_prompt = f"""
    너는 고등학교 1학년 학생의 다정한 진로 비서야. 성격은 '{persona}' 스타일로 대답해줘.
    [우리 학교 정보 데이터]
    {school_knowledge}
    
    [답변 약속]
    1. [핵심요약]: 답변의 결론을 맨 처음에 1-2줄로 요약.
    2. [자세한설명]: 제공된 파일 데이터에 근거하여 구체적으로 설명.
    3. 반드시 한국어로 답변할 것.
    """
    
    with st.chat_message("assistant"):
        try:
            response = model.generate_content(system_prompt, stream=True)
            def stream_gen():
                for chunk in response:
                    if chunk.text: yield chunk.text
            full_text = st.write_stream(stream_gen())
            
            try:
                summary = full_text.split("[자세한설명]")[0].replace("[핵심요약]", "").strip()
            except:
                summary = full_text
            
            new_row = pd.DataFrame([{
                "날짜": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "학번": student_id, "이름": student_name, "주제": topic,
                "비서성격": persona, "질문내용": user_question, "AI답변": summary
            }])
            conn.update(worksheet="질문기록", data=pd.concat([df, new_row], ignore_index=True))
            
        except Exception as e:
            st.error(f"상담 중 오류가 발생했습니다: {e}")
