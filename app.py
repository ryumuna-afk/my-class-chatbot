import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import os

# ==========================================
# 1. 페이지 및 기본 환경 설정
# ==========================================
st.set_page_config(page_title="꿈-잇(IT) 비서", page_icon="🤖", layout="wide")

# 표 인식과 문맥 파악에 가장 강력한 2.0 엔진 사용
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.0-flash') 
conn = st.connection("gsheets", type=GSheetsConnection)

# ==========================================
# 2. 학교 공식 자료 자동 로드
# ==========================================
@st.cache_data
def load_global_files():
    file_parts = []
    valid_extensions = (".pdf", ".xlsx", ".xls", ".csv", ".png", ".jpg", ".jpeg")
    target_files = [f for f in os.listdir(".") if f.lower().endswith(valid_extensions)]
    
    for file_name in target_files:
        try:
            lower_name = file_name.lower()
            if lower_name.endswith(".pdf"):
                with open(file_name, "rb") as f:
                    file_parts.append({
                        "mime_type": "application/pdf",
                        "data": f.read()
                    })
            elif lower_name.endswith((".xlsx", ".xls", ".csv")):
                if lower_name.endswith(".csv"):
                    df_file = pd.read_csv(file_name)
                else:
                    df_file = pd.read_excel(file_name)
                excel_text = f"\n--- [학교 엑셀/CSV 자료: {file_name}] ---\n{df_file.to_csv(index=False)}\n"
                file_parts.append(excel_text)
            elif lower_name.endswith((".png", ".jpg", ".jpeg")):
                mime_type = "image/png" if lower_name.endswith(".png") else "image/jpeg"
                with open(file_name, "rb") as f:
                    file_parts.append({
                        "mime_type": mime_type,
                        "data": f.read()
                    })
        except Exception as e: 
            continue
    return file_parts

global_school_files = load_global_files()

# ==========================================
# 3. 비밀코드 학생 인증
# ==========================================
secret_code = st.query_params.get("id")
if not secret_code:
    st.error("🚨 올바른 전용 링크로 접속해 주세요.")
    st.stop()

try:
    student_db = conn.read(worksheet="학생명단", ttl=600)
    matched_student = student_db[student_db['비밀코드'] == secret_code]
    if matched_student.empty:
        st.error("🚨 유효하지 않은 비밀코드입니다.")
        st.stop()
    student_id = str(matched_student.iloc[0]['학번'])
    student_name = matched_student.iloc[0]['이름']
except:
    st.error("서버 연결에 실패했습니다. (학생 명단 확인 불가)")
    st.stop()

# ==========================================
# 4. 🎨 UI 영역 1: 사이드바 (관리자 전용)
# ==========================================
with st.sidebar:
    st.markdown("### 🔐 교사용 관리 메뉴")
    st.caption("공식 학교 자료 업로드 및 관리")
    
    if st.text_input("비밀번호 입력", type="password") == "0486":
        if st.button("🔄 깃허브 데이터 동기화 (캐시 초기화)"):
            load_global_files.clear() 
            st.success("동기화 완료! 새 파일을 인식합니다.")
            st.rerun() 
            
        file = st.file_uploader("새 학교 자료 업로드", type=["pdf", "xlsx", "xls", "csv", "png", "jpg", "jpeg"])
        if file:
            with open(file.name, "wb") as f: 
                f.write(file.getbuffer())
            load_global_files.clear()
            st.success(f"'{file.name}' 업데이트 완료!")

# ==========================================
# 5. 🌟 UI 영역 2: 메인 화면 (모바일 최적화)
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

# 대화 기록 로드 및 표시
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
    my_records = pd.DataFrame()

# ==========================================
# 6. 💬 채팅 처리 (문맥 기억 구조 최적화)
# ==========================================
if user_question := st.chat_input("질문을 입력하세요!"):
    
    with st.chat_message("user"):
        st.write(user_question)
        
    system_prompt = f"""
    당신은 고등학교 진로 상담 비서입니다. (선택된 페르소나: {persona})

    [답변 가이드라인]
    1. 함께 전달된 [학교 공식 원본 문서들]을 분석하여 '정확하고 직접적인 답'을 찾으십시오.
    2. 정답을 찾았다면 선택된 페르소나의 말투에 어울리는 '자연스러운 한두 문장'으로 대답하십시오. 서론이나 불필요한 TMI는 절대 금지입니다.
    3. 데이터에 질문에 대한 명확한 답이 없다면, AI의 일반 지식으로 유익하게 답변하되, 마지막에 반드시 "이는 일반적인 내용이므로, 정확한 내용은 학교나 선생님께 꼭 다시 확인해 봐!"라고 덧붙이십시오.
    """
    
    # 최근 3번의 대화 흐름 구성
    recent_context = ""
    if not my_records.empty:
        recent_context = "【최근 대화 맥락】\n"
        for _, row in my_records.tail(3).iterrows():
            recent_context += f"- 학생: {row['질문내용']}\n- 비서: {row['AI답변']}\n"
        recent_context += "\n🚨주의🚨: 위 대화 맥락을 반드시 기억하십시오! 학생의 새로운 질문이 짧은 단어(예: '1학년')라면, 직전 대화 주제에 대한 꼬리 질문입니다.\n\n"

    with st.chat_message("assistant"):
        try:
            # 🌟 [해결의 열쇠: 프롬프트 조립 순서 변경]
            prompt_parts = [system_prompt]
            
            # 1. 학교 전체 파일을 먼저 투입 (AI가 문서를 먼저 훑어보게 함)
            if global_school_files:
                prompt_parts.extend(global_school_files)

            # 2. 마지막에 [최근 대화 맥락]과 [새로운 질문]을 묶어서 투입 (가장 강력하게 기억하도록 유도)
            final_query = recent_context + f"【학생의 새로운 질문】: {user_question}"
            prompt_parts.append(final_query)

            # 답변 생성
            response = model.generate_content(prompt_parts, stream=True)
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
