import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import os
from PIL import Image

# ==========================================
# 1. 페이지 및 기본 환경 설정
# ==========================================
st.set_page_config(page_title="꿈-잇(IT) 비서", page_icon="🤖", layout="wide")

# 제미나이 2.0 모델 설정
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.0-flash') 
conn = st.connection("gsheets", type=GSheetsConnection)

# ==========================================
# 2. 학교 공식 자료 로드 (PDF, 엑셀, 이미지 모두 Vision 인식)
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
                    file_parts.append({"mime_type": "application/pdf", "data": f.read()})
            elif lower_name.endswith((".xlsx", ".xls", ".csv")):
                if lower_name.endswith(".csv"): df_file = pd.read_csv(file_name)
                else: df_file = pd.read_excel(file_name)
                excel_text = f"\n--- [학교 자료: {file_name}] ---\n{df_file.to_csv(index=False)}\n"
                file_parts.append(excel_text)
            elif lower_name.endswith((".png", ".jpg", ".jpeg")):
                mime_type = "image/png" if lower_name.endswith(".png") else "image/jpeg"
                with open(file_name, "rb") as f:
                    file_parts.append({"mime_type": mime_type, "data": f.read()})
        except: continue
    return file_parts

global_school_files = load_global_files()

# ==========================================
# 3. 학생 인증
# ==========================================
secret_code = st.query_params.get("id")
if not secret_code:
    st.error("🚨 전용 링크로 접속해 주세요.")
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
    st.error("서버 연결에 실패했습니다.")
    st.stop()

# ==========================================
# 4. 사이드바 (교사용 관리 메뉴)
# ==========================================
with st.sidebar:
    st.markdown("### 🔐 교사용 관리 메뉴")
    if st.text_input("비밀번호 입력", type="password") == "0486":
        if st.button("🔄 데이터 동기화 (새 파일 반영)"):
            load_global_files.clear() 
            st.rerun() 
        file = st.file_uploader("새 학교 자료 업로드", type=["pdf", "xlsx", "xls", "csv", "png", "jpg", "jpeg"])
        if file:
            with open(file.name, "wb") as f: f.write(file.getbuffer())
            load_global_files.clear()
            st.success("업데이트 완료!")

# ==========================================
# 5. 메인 화면
# ==========================================
st.markdown("### 🤖 꿈-잇(IT) 비서 : 나만의 진로·학업 메이트")
st.markdown(f"**반가워요, {student_name} 학생!** 🎓")
st.markdown("---")

col1, col2 = st.columns(2)
with col1: persona = st.selectbox("🤖 비서 성격", ["다정한 친구", "꼼꼼한 비서", "냉철한 전략가"])
with col2: topic = st.selectbox("📌 상담 주제", ["① 학교생활 적응", "② 진로 탐색", "③ 상급학년 준비"])

st.info("💡 학교생활, 진로, 과목 선택 등 궁금한 점을 질문해 보세요!")
st.markdown("---")

# 대화 기록 로드
try:
    df = conn.read(worksheet="질문기록", ttl=0).dropna(how='all')
    my_records = df[df['학번'] == student_id]
    for _, row in my_records.tail(5).iterrows(): # 최근 5개만 표시
        with st.chat_message("user"): st.write(row['질문내용'])
        with st.chat_message("assistant"): st.write(row['AI답변'])
except: df = pd.DataFrame(columns=["날짜", "학번", "이름", "주제", "비서성격", "질문내용", "AI답변"])

# ==========================================
# 6. 채팅 처리 (문맥 기억 및 파일 분석)
# ==========================================
if user_question := st.chat_input("질문을 입력하세요!"):
    with st.chat_message("user"): st.write(user_question)
    
    # 이전 대화 기억(Context) 구성
    recent_context = ""
    if not my_records.empty:
        recent_context = "【최근 대화 맥락】\n"
        for _, row in my_records.tail(3).iterrows():
            recent_context += f"- 학생: {row['질문내용']}\n- 비서: {row['AI답변']}\n"
        recent_context += "\n🚨주의🚨: 위 맥락을 기억하고, 짧은 질문(예: '1학년은?')은 이전 대화 주제에 대한 꼬리 질문으로 해석해.\n\n"

    system_prompt = f"""
    당신은 고등학교 진로 상담 비서({persona})입니다.
    1. 첨부된 학교 자료(PDF, 엑셀, 이미지)를 눈으로 직접 보고 '정확하고 직접적인 답'을 최우선으로 찾으십시오.
    2. 이전 대화 맥락을 고려하여 질문의 진짜 의도를 파악하십시오.
    3. 답이 없으면 일반 지식으로 조언하고, 마지막에 "정확한 내용은 담임 선생님께 확인해 봐!"라고 덧붙이십시오.
    """
    
    with st.chat_message("assistant"):
        try:
            prompt_parts = [system_prompt, recent_context, f"학생 질문: {user_question}"]
            if global_school_files: prompt_parts.extend(global_school_files)

            response = model.generate_content(prompt_parts, stream=True)
            def stream_gen():
                for chunk in response:
                    if chunk.text: yield chunk.text
            full_text = st.write_stream(stream_gen())
            
            new_row = pd.DataFrame([{
                "날짜": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "학번": student_id, "이름": student_name, "주제": topic,
                "비서성격": persona, "질문내용": user_question, "AI답변": full_text
            }])
            conn.update(worksheet="질문기록", data=pd.concat([df, new_row], ignore_index=True))
        except Exception as e:
            st.error(f"오류: {e}")
