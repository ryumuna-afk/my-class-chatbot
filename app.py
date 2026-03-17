import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import os

# ==========================================
# 1. 페이지 및 기본 환경 설정
# ==========================================
st.set_page_config(page_title="진로 메이트", page_icon="🤝", layout="wide")

# 🌟 [디자인 추가] 챗봇 입력창 및 화이트보드 스크롤 스타일 🌟
st.markdown("""
<style>
    /* 챗봇 입력창 테두리 및 그림자 효과 */
    [data-testid="stChatInput"] {
        border: 2px solid #4CAF50 !important;
        border-radius: 15px !important;
        box-shadow: 0px 0px 15px rgba(76, 175, 80, 0.4) !important;
        background-color: #F9FFF9 !important;
    }
    
    [data-testid="stChatInput"] textarea {
        font-size: 17px !important;
        font-weight: bold !important;
    }
    
    /* 선생님의 화이트보드(알림장) 디자인 */
    .memo-board {
        background-color: #FFFDE7;
        padding: 15px 20px;
        border-radius: 10px;
        border-left: 6px solid #FFD54F;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        font-size: 16px;
        max-height: 150px;
        overflow-y: auto;
    }
    
    .memo-board::-webkit-scrollbar { width: 6px; }
    .memo-board::-webkit-scrollbar-thumb { background-color: #FFD54F; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.0-flash') 
conn = st.connection("gsheets", type=GSheetsConnection)

# ==========================================
# 2. 🌟 학교 공식 자료 로드
# ==========================================
@st.cache_data
def load_global_files():
    file_dict = {} 
    valid_extensions = (".pdf", ".xlsx", ".xls", ".csv", ".png", ".jpg", ".jpeg")
    target_files = [f for f in os.listdir(".") if f.lower().endswith(valid_extensions)]
    
    for file_name in target_files:
        try:
            lower_name = file_name.lower()
            if lower_name.endswith(".pdf"):
                with open(file_name, "rb") as f: file_dict[file_name] = {"mime_type": "application/pdf", "data": f.read()}
            elif lower_name.endswith((".xlsx", ".xls", ".csv")):
                df_file = pd.read_csv(file_name) if lower_name.endswith(".csv") else pd.read_excel(file_name)
                file_dict[file_name] = f"\n--- [학교 자료: {file_name}] ---\n{df_file.to_csv(index=False)}\n"
            elif lower_name.endswith((".png", ".jpg", ".jpeg")):
                mime_type = "image/png" if lower_name.endswith(".png") else "image/jpeg"
                with open(file_name, "rb") as f: file_dict[file_name] = {"mime_type": mime_type, "data": f.read()}
        except Exception: continue
    return file_dict

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
    try:
        student_holland = str(matched_student.iloc[0]['홀랜드유형'])
        if student_holland == "nan" or student_holland.strip() == "": student_holland = "아직 검사 안 함"
    except: student_holland = "정보 없음" 
except:
    st.error("서버 연결에 실패했습니다. (학생 명단 확인 불가)")
    st.stop()

# 📌 화이트보드 내용 불러오기
try:
    student_memo_df = conn.read(worksheet="화이트보드", ttl=0).dropna(how='all')
    board_text = str(student_memo_df.iloc[0]['내용']) if not student_memo_df.empty else ""
    if board_text == "nan": board_text = ""
except: board_text = ""

# ==========================================
# 4. 🎨 UI 영역 1: 사이드바 (교사 전용)
# ==========================================
with st.sidebar:
    st.markdown("### 🔐 교사용 관리 메뉴")
    if st.text_input("비밀번호 입력", type="password") == "0486":
        st.markdown("---")
        st.markdown("#### 📝 학급 화이트보드")
        new_memo = st.text_area("알림장 내용을 적어주세요.", value=board_text, height=150)
        if st.button("📢 화이트보드 업데이트!"):
            conn.update(worksheet="화이트보드", data=pd.DataFrame([{"내용": new_memo}]))
            st.success("✅ 업데이트 완료!")
            st.rerun()

        st.markdown("---")
        st.markdown("#### 📁 학교 자료 업데이트")
        if st.button("🔄 데이터 동기화"):
            load_global_files.clear() 
            st.rerun() 
            
        file = st.file_uploader("새 학교 자료 업로드", type=["pdf", "xlsx", "xls", "csv", "png", "jpg", "jpeg"])
        if file:
            with open(file.name, "wb") as f: f.write(file.getbuffer())
            load_global_files.clear()
            st.success(f"업데이트 완료!")
            
        st.markdown("---")
        st.markdown("#### 📋 접수된 학생 문의 확인")
        try:
            inquiry_df = conn.read(worksheet="상담문의", ttl=0).dropna(how='all')
            if not inquiry_df.empty: st.dataframe(inquiry_df, use_container_width=True)
            else: st.info("문의가 없습니다.")
        except: st.error("구글 시트 연동 오류")

# ==========================================
# 5. 🌟 UI 영역 2: 메인 화면
# ==========================================
st.markdown("## 🤝 너의 진로·학업 에이전틱 IT 단짝, 『진로 메이트』")
st.markdown(f"**반가워요, {student_name} 학생! 나의 미래를 스케치해 볼까요? 🎨**")

if board_text.strip():
    formatted_text = board_text.replace('\n', '<br>')
    st.markdown(f"""
    <div class="memo-board">
        <strong>📌 [담임 선생님의 알림장]</strong><br><br>{formatted_text}
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

col1, col2 = st.columns(2)
with col1: persona = st.selectbox("🤖 메이트 성향", ["다정한 멘토", "창의적인 예술가", "냉철한 분석가"])
with col2: topic = st.selectbox("📌 상담 주제", ["① 학교생활 적응", "② 진로 탐색", "③ 상급학년 준비", "④ 📚 꼬.꼬.독 (진로 독서)", "⑤ ✨ 융합 창직 스튜디오 (나만의 직업 만들기)"])

st.markdown("#### 🔗 학급 공식 채널 바로가기")
col_btn1, col_btn2, col_btn3 = st.columns(3)
with col_btn1: st.link_button("📁 학교자료", "https://drive.google.com/drive/folders/10c4fu9UtAyQGwlUSlm4YeCf5dbacL7Gr", use_container_width=True)
with col_btn2: st.link_button("🏫 클래스룸", "https://classroom.google.com/c/ODQ4MTc2OTgyNDcx?cjc=k2vj6lne", use_container_width=True)
with col_btn3: st.link_button("📅 학급캘린더", "https://calendar.google.com/calendar/u/0?cid=NWIxZWJlZDYxNjY1Y2VhOTQyMGI1Y2I2MzYzMjE4ZTM0ZWRlMjlhMGI3NzFiZmI1MGM4NzE2Yzg4ZTA3YmE2ZUBncm91cC5jYWxlbmRhci5nb29nbGUuY29t", use_container_width=True)

st.markdown("#### 🧭 나의 진로 DNA 찾기 (심리검사)")
st.link_button("🔍 커리어넷 직업흥미검사(H형)", "https://www.career.go.kr/cnet/front/examen/inspctMain.do", use_container_width=True)

st.markdown("---")

# 선생님께 문의 남기기
with st.expander("📬 AI 메이트가 아닌, 담임 선생님께 직접 문의 남기기"):
    inquiry_text = st.text_area("상담/문의 내용", label_visibility="collapsed")
    if st.button("선생님께 전송하기"):
        if inquiry_text:
            try:
                try: inq_df = conn.read(worksheet="상담문의", ttl=0)
                except: inq_df = pd.DataFrame(columns=["날짜", "학번", "이름", "문의내용"])
                new_inq = pd.DataFrame([{"날짜": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "학번": student_id, "이름": student_name, "문의내용": inquiry_text}])
                conn.update(worksheet="상담문의", data=pd.concat([inq_df, new_inq], ignore_index=True))
                st.success("✅ 선생님께 전달되었습니다!")
            except: st.error("전송 실패!")

st.markdown("---")

# ==========================================
# 6. 💬 채팅 처리 (실시간 Session State 메모리 적용)
# ==========================================
try:
    df = conn.read(worksheet="질문기록", ttl=0).dropna(how='all')
except:
    df = pd.DataFrame(columns=["날짜", "학번", "이름", "주제", "메이트성향", "질문내용", "AI답변"])

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
    my_records = df[df['학번'] == student_id]
    if not my_records.empty:
        for _, row in my_records.tail(8).iterrows(): 
            st.session_state.chat_history.append({"role": "user", "content": row['질문내용']})
            st.session_state.chat_history.append({"role": "assistant", "content": row['AI답변']})

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if user_question := st.chat_input("👉 이곳을 터치해서 메이트에게 질문이나 생각을 입력하세요! 👈"):
    
    st.session_state.chat_history.append({"role": "user", "content": user_question})
    with st.chat_message("user"):
        st.write(user_question)
        
    recent_context = "👇 [AI가 반드시 기억해야 할 이전 대화 기록] 👇\n"
    for msg in st.session_state.chat_history[-7:-1]:
        role_name = "학생의 질문" if msg["role"] == "user" else "너(AI)의 이전 대답"
        recent_context += f"▶ {role_name}: {msg['content']}\n"
    recent_context += "--------------------------------------\n"

    selected_file_parts = []
    if global_school_files:
        file_names_str = ", ".join(global_school_files.keys())
        router_prompt = f"""학생 질문: "{user_question}" / 이전 대화 맥락: "{recent_context}"
        위 질문과 맥락이 학교 보유 파일 [{file_names_str}] 중 어느 것과 관련 있는지 파일명만 쉼표로 적으세요. 없으면 '없음'."""
        try:
            router_answer = model.generate_content(router_prompt).text
            for fname, fcontent in global_school_files.items():
                if fname in router_answer: selected_file_parts.append(fcontent)
        except: pass
        
    # 🌟 [창직 스튜디오 & 꼬꼬독 프롬프트 고도화] 🌟
    system_prompt = f"""
    당신은 고교학점제 맞춤형 진로 길잡이인 '에이전틱 AI 진로 메이트'입니다. (선택된 페르소나: {persona})
    - 학생 이름: {student_name} / 흥미 유형(홀랜드): {student_holland} / 현재 상담 주제: {topic}
    """
    
    if board_text.strip():
        system_prompt += f"\n[현재 담임 선생님의 화이트보드(알림장) 공지사항]\n{board_text}\n"
        
    system_prompt += f"""
    [행동 수칙]
    1. 🚨맥락 파악 철칙🚨: 함께 전달된 [이전 대화 기록]을 최우선으로 분석하십시오. 학생이 단답형으로 대답했다면 당신이 직전에 던진 꼬리질문에 대한 답이므로, 절대 되묻지 말고 논리를 전개하십시오.
    2. 🌟[주제 4] 꼬.꼬.독 모드🌟: 학생이 책 내용을 말하면 (1)공감/칭찬 ➡ (2)유익한 조언 추가 ➡ (3)사고를 확장하는 '꼬리 질문 1개'를 던지십시오.
    
    3. ✨[주제 5] 융합 창직 스튜디오 모드 (매우 중요)✨: 
       - 학생의 홀랜드 유형과 관심사를 융합해 **세상에 없는 새로운 직업(창직)**을 설계하도록 돕는 모드입니다.
       - 학생이 키워드나 관심사를 던지면, 기발한 미래 직업 아이디어를 제안하며 호기심을 자극하십시오.
       - "이 직업의 멋진 이름(명함)을 무엇이라고 지을까?", "이 직업은 사회의 어떤 문제를 가장 먼저 해결해야 할까?" 등 상상력을 키우는 질문을 던지십시오.
       - 최종적으로 **"이 직업인이 되기 위해 고등학교 2학년 때 어떤 선택과목들을 융합해서 들으면 좋을까?"**라고 질문하여, 학생이 스스로 고교학점제 과목 로드맵을 짜도록 유도하십시오.
       
    4. 🚨모를 때의 대처🚨: 학교 자료에 없는 민감한 학사 정보는 "제가 가진 자료에는 없네요. 선생님께 여쭤보는 건 어떨까?"라고 대답하십시오.
    5. 🚨출력 형식 주의🚨: 물결표(~) 기호 사용 금지. 하이픈(-)이나 한글(부터 ~ 까지)을 사용하십시오.
    """
    
    with st.chat_message("assistant"):
        try:
            try:
                school_data_df = conn.read(worksheet="학교자료", ttl=600).dropna(how='all')
                sheet_context = "\n\n[실시간 학교 자료]\n"
                for _, row in school_data_df.iterrows(): sheet_context += f"- {row['구분']}: {row['내용']}\n"
            except: sheet_context = "" 

            prompt_query = f"{recent_context}\n\n위의 [이전 대화 기록]을 먼저 읽고, 학생의 방금 전 대답(현재 질문)이 직전 대화와 어떻게 이어지는지 파악한 뒤 대답하십시오.\n\n[학생의 현재 질문]: {user_question}{sheet_context}"
            prompt_parts = [system_prompt, prompt_query]
            if selected_file_parts: prompt_parts.extend(selected_file_parts)

            response = model.generate_content(prompt_parts, stream=True)
            def stream_gen():
                for chunk in response:
                    if chunk.text: yield chunk.text
            full_text = st.write_stream(stream_gen())
            
            st.session_state.chat_history.append({"role": "assistant", "content": full_text})
            
            new_row = pd.DataFrame([{
                "날짜": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "학번": student_id, "이름": student_name, "주제": topic,
                "메이트성향": persona, "질문내용": user_question, "AI답변": full_text
            }])
            conn.update(worksheet="질문기록", data=pd.concat([df, new_row], ignore_index=True))
            
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
