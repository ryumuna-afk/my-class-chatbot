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

# 3. 모든 PDF 통합 로드 함수 (데이터 유실 방지)
@st.cache_data
def load_all_pdf_data():
    combined_text = ""
    pdf_files = [f for f in os.listdir(".") if f.endswith(".pdf")]
    
    if not pdf_files:
        return "학습된 학교 자료가 없습니다."

    for file_name in pdf_files:
        try:
            with open(file_name, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                combined_text += f"\n--- {file_name} 내용 시작 ---\n"
                for page in reader.pages:
                    combined_text += page.extract_text() + "\n"
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
    st.error("인증 정보를 불러오지 못했습니다.")
    st.stop()

# ==========================================
# 🎨 UI 영역: 사이드바
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

    with st.expander("🔐 관리자 (데이터 확인)"):
        if st.text_input("PW", type="password") == "0486":
            st.write(f"📝 데이터 크기: {len(school_knowledge)}자")
            if st.button("캐시 초기화"):
                load_all_pdf_data.clear()
                st.rerun()

# ==========================================
# 🌟 메인 화면 (가이드 가시성 강화)
# ==========================================
st.title("🤖 꿈-잇(IT) 비서 : 나만의 진로·학업 메이트")

# 
# 요약 설명 (선생님 요청 반영!)
if topic == "① 학교생활 적응":
    st.info("📘 **[학교생활 적응]** 학사 일정, 생활 규정, 급식/동아리/봉사활동 정보를 알려줄게!")
elif topic == "② 진로 탐색":
    st.info("🔍 **[진로 탐색]** 나에게 맞는 직업/학과 추천과 생기부용 독서/활동을 추천해줄게!")
elif topic == "③ 상급학년 준비":
    st.info("🎯 **[상급학년 준비]** 2학년 선택과목 가이드와 수강 신청 꿀팁을 확인해봐!")

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

# 💬 채팅 처리 (유연한 답변 로직)
if user_question := st.chat_input("궁금한 점을 물어보세요!"):
    with st.chat_message("user"):
        st.write(f"**[{topic}]** {user_question}")
        
    # 🌟 프롬프트를 부드럽고 명확하게 수정
    system_prompt = f"""
    너는 고등학교 진로 비서야. 학생 이름은 {student_name}이야. 
    성격은 '{persona}' 스타일로 다정하게 대답해줘.
    
    [지침]
    1. 아래 제공된 [학교 자료]에서 질문에 대한 답을 먼저 찾아봐.
    2. 자료에 구체적인 내용(전화번호, 날짜 등)이 있다면 반드시 그 내용을 포함해줘.
    3. 자료에 없더라도 네가 아는 상식 내에서 학생에게 도움이 될 따뜻한 조언을 해줘.
    4. 답변은 [핵심요약]과 [자세한설명]으로 나누어 작성해줘.
    
    [학교 자료]
    {school_knowledge}
    """
    
    with st.chat_message("assistant"):
        try:
            # 🚀 스트리밍 생성
            response = model.generate_content(system_prompt, stream=True)
            
            # 실시간으로 화면에 출력 (이 코드가 답변을 즉시 보여줍니다)
            def stream_gen():
                for chunk in response:
                    if chunk.text: yield chunk.text
            
            full_text = st.write_stream(stream_gen())
            
            # 저장용 요약본 (태그가 없어도 전체 내용을 저장하도록 안전장치)
            if "[자세한설명]" in full_text:
                summary = full_text.split("[자세한설명]")[0].replace("[핵심요약]", "").strip()
            else:
                summary = full_text[:100] # 태그가 없으면 앞부분만 저장
            
            # 구글 시트에 기록 저장
            new_row = pd.DataFrame([{
                "날짜": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "학번": student_id, "이름": student_name, "주제": topic,
                "비서성격": persona, "질문내용": user_question, "AI답변": full_text # 시트에는 전체 답변 저장
            }])
            conn.update(worksheet="질문기록", data=pd.concat([df, new_row], ignore_index=True))
            
        except Exception as e:
            st.error(f"상담 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요! ({e})")
