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

# 🌟 [디자인 추가] 챗봇 질문 입력창 화려하게 강조하기 CSS 🌟
st.markdown("""
<style>
    /* 챗봇 입력창 테두리 및 그림자 효과 */
    [data-testid="stChatInput"] {
        border: 2px solid #FF4B4B !important; /* 눈에 띄는 빨간색 테두리 */
        border-radius: 15px !important; /* 부드러운 둥근 모서리 */
        box-shadow: 0px 0px 15px rgba(255, 75, 75, 0.4) !important; /* 네온 빛 그림자 효과 */
        background-color: #FFF9F9 !important; /* 아주 연한 핑크빛 배경 */
    }
    
    /* 입력창 안의 글씨 크기와 굵기 키우기 */
    [data-testid="stChatInput"] textarea {
        font-size: 17px !important;
        font-weight: bold !important;
    }
</style>
""", unsafe_allow_html=True)

# 표 인식과 사진 분석에 강력한 2.0 엔진 사용
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.0-flash') 
conn = st.connection("gsheets", type=GSheetsConnection)

# ==========================================
# 2. 🌟 학교 공식 자료 로드 (비용 절감: 서랍장 형태)
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
                with open(file_name, "rb") as f:
                    file_dict[file_name] = {"mime_type": "application/pdf", "data": f.read()}
            elif lower_name.endswith((".xlsx", ".xls", ".csv")):
                if lower_name.endswith(".csv"):
                    df_file = pd.read_csv(file_name)
                else:
                    df_file = pd.read_excel(file_name)
                excel_text = f"\n--- [학교 엑셀/CSV 자료: {file_name}] ---\n{df_file.to_csv(index=False)}\n"
                file_dict[file_name] = excel_text
            elif lower_name.endswith((".png", ".jpg", ".jpeg")):
                mime_type = "image/png" if lower_name.endswith(".png") else "image/jpeg"
                with open(file_name, "rb") as f:
                    file_dict[file_name] = {"mime_type": mime_type, "data": f.read()}
        except Exception as e: 
            continue
    return file_dict

global_school_files = load_global_files()

# ==========================================
# 3. 비밀코드 학생 인증 및 홀랜드 유형 로드
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
        if student_holland == "nan" or student_holland.strip() == "":
            student_holland = "아직 검사 안 함"
    except:
        student_holland = "정보 없음" 
        
except:
    st.error("서버 연결에 실패했습니다. (학생 명단 확인 불가)")
    st.stop()

# ==========================================
# 4. 🎨 UI 영역 1: 사이드바 (교사 전용 메뉴)
# ==========================================
with st.sidebar:
    st.markdown("### 🔐 교사용 관리 메뉴")
    st.caption("공식 학교 자료 업로드 및 문의 확인")
    
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
            
        st.markdown("---")
        st.markdown("#### 📋 접수된 학생 문의 확인")
        try:
            inquiry_df = conn.read(worksheet="상담문의", ttl=0).dropna(how='all')
            if not inquiry_df.empty:
                st.dataframe(inquiry_df, use_container_width=True)
            else:
                st.info("새로 접수된 문의가 없습니다.")
        except:
            st.error("구글 시트에 '상담문의' 시트가 있는지 확인해주세요.")

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
    topic = st.selectbox("📌 상담 주제", ["① 학교생활 적응", "② 진로 탐색", "③ 상급학년 준비", "④ 📚 꼬.꼬.독 (진로 독서)"])

# 🌟 1. 학급 공식 채널 (드라이브 & 캘린더) 바로가기 단추
st.markdown("#### 🔗 학급 공식 채널 바로가기")
col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    st.link_button("📁 학교안내자료 모음", "https://drive.google.com/drive/folders/10c4fu9UtAyQGwlUSlm4YeCf5dbacL7Gr", use_container_width=True)
with col_btn2:
    # 선생님의 실제 구글 캘린더 공유 링크로 나중에 바꿔주세요!
    st.link_button("📅 우리 반 학급 캘린더", "여기에_학급캘린더_링크_붙여넣기", use_container_width=True)

# 🌟 2. 진로 심리검사 바로가기 단추
st.markdown("#### 🧭 나의 진로 DNA 찾기 (심리검사)")
col_test1, col_test2 = st.columns(2)
with col_test1:
    st.link_button("💡 1분 컷! 퀵 학습성향검사", "https://cures.kr/recommend/jobPreferenceTest.do", use_container_width=True)
with col_test2:
    st.link_button("🔍 정밀 진단! 커리어넷 직업흥미검사(H형)", "https://www.career.go.kr/cnet/front/examen/inspctMain.do", use_container_width=True)

st.markdown("---")

if topic == "① 학교생활 적응":
    st.info("📘 **[학교생활 적응]** 학교, 담임선생님이 안내한 정보를 물어보세요.")
elif topic == "② 진로 탐색":
    st.info("🔍 **[진로 탐색]** 직업/학과 가이드, 추천 도서, 진로 설계 사례를 물어보세요.")
elif topic == "③ 상급학년 준비":
    st.info("🎯 **[상급학년 준비]** 선택과목 특징, 전공별 권장 과목 조합을 물어보세요.")
elif topic == "④ 📚 꼬.꼬.독 (진로 독서)":
    st.info("📚 **[꼬.꼬.독 프로젝트]** 읽은 책 제목이나 기억에 남는 내용을 말해주세요! 생각의 꼬리를 무는 재미있는 질문을 던져줄게요.")

# 선생님께 문의 남기기 (메인 화면 접이식 메뉴)
with st.expander("📬 AI 비서가 아닌, 선생님께 직접 문의 남기기"):
    st.caption("상담 예약이나 선생님께 직접 물어보고 싶은 내용을 적어주세요.")
    inquiry_text = st.text_area("상담/문의 내용", placeholder="예) 다음 주 수요일 점심시간에 진로 상담 가능한가요?", label_visibility="collapsed")
    if st.button("선생님께 전송하기"):
        if inquiry_text:
            try:
                try:
                    inq_df = conn.read(worksheet="상담문의", ttl=0)
                except:
                    inq_df = pd.DataFrame(columns=["날짜", "학번", "이름", "문의내용"])
                new_inq = pd.DataFrame([{
                    "날짜": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "학번": student_id, "이름": student_name, "문의내용": inquiry_text
                }])
                conn.update(worksheet="상담문의", data=pd.concat([inq_df, new_inq], ignore_index=True))
                st.success("✅ 선생님께 문의가 성공적으로 전달되었습니다!")
            except Exception as e:
                st.error("전송에 실패했습니다. 관리자에게 문의하세요.")
        else:
            st.warning("문의 내용을 먼저 입력해 주세요!")

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
    my_records = pd.DataFrame()

# ==========================================
# 6. 💬 채팅 처리 (입력창 안내 문구 수정됨)
# ==========================================
if user_question := st.chat_input("👉 이곳을 터치해서 챗봇에게 대답이나 질문을 입력하세요! 👈"):
    
    with st.chat_message("user"):
        st.write(user_question)
        
    recent_context = ""
    if not my_records.empty:
        recent_context = "[이전 대화 맥락 (매우 중요)]\n"
        for _, row in my_records.tail(5).iterrows():
            recent_context += f"학생: {row['질문내용']}\n비서: {row['AI답변']}\n"

    selected_file_parts = []
    if global_school_files:
        file_names_str = ", ".join(global_school_files.keys())
        router_prompt = f"""
        학생 질문: "{user_question}"
        이전 대화 맥락: "{recent_context}"
        학교 보유 파일 목록: [{file_names_str}]
        당신은 눈치가 아주 빠른 자료 분류 전문가입니다. 
        학생의 질문 내용이 위 파일들 중 '어느 파일 안에 포함되어 있을지' 논리적으로 짐작하고 추론하세요.
        - 애매하면 관련된 파일을 모두 고르세요.
        - 답변 규칙: 관련된 파일 이름만 쉼표(,)로 구분해서 적으세요. 전혀 관련 없는 질문에만 '없음'이라고 적으세요.
        """
        try:
            router_response = model.generate_content(router_prompt)
            router_answer = router_response.text
            for fname, fcontent in global_school_files.items():
                if fname in router_answer:
                    selected_file_parts.append(fcontent)
        except:
            pass
        
    # 🌟 [꼬꼬독 조언+질문 콤보 프롬프트] 🌟
    system_prompt = f"""
    당신은 고등학교 진로 상담 비서입니다. (선택된 페르소나: {persona})
    
    [현재 대화 중인 학생의 비밀 프로필]
    - 학생 이름: {student_name}
    - 직업흥미(홀랜드 유형): {student_holland}
    - 현재 선택한 상담 주제: {topic}

    [행동 수칙]
    1. 🚨주제 이탈 금지🚨: 만약 학생의 질문이 학교생활, 진로 탐색, 상급학년 준비, 독서와 관련 없는 내용이라면, 절대 답변하지 말고 단호하게 끊어주십시오.
    2. 🌟꼬.꼬.독 모드 멘토링 지침 (가장 중요)🌟: 
       - 현재 주제가 '④ 📚 꼬.꼬.독 (진로 독서)'일 경우, 당신은 학생의 생각을 끌어내면서도 방향을 잡아주는 **유능한 독서 멘토**입니다.
       - **[이전 대화 맥락]을 반드시 확인하고, 학생이 방금 뱉은 가장 마지막 대답과 100% 연결되게 말하십시오.**
       - (1단계 - 공감) 학생이 방금 말한 핵심 단어나 문장을 인용하며 폭풍 공감과 칭찬을 해줍니다. 
       - (2단계 - 조언) 학생의 생각에 살을 붙여줄 수 있는 **'짧고 유익한 조언이나 새로운 시각(전문적 인사이트)'**을 가볍게 하나 제공합니다.
       - (3단계 - 꼬리질문) 조언을 바탕으로, 한 단계 더 깊이 파고드는 **'꼬리 질문 딱 1개'**를 던지십시오.
       - 🚨주의🚨: 조언이 너무 길어지면 지루해집니다. 짧고 임팩트 있게 멘토링한 뒤, 반드시 '질문'으로 마침표를 찍어 학생이 대답하게 만드십시오.
    3. 🌟홀랜드 맞춤형 컨설팅🌟: 학생이 진로나 선택과목을 물어볼 때, 학생의 홀랜드 유형({student_holland})을 반영하여 추천해 주십시오. (정보가 없으면 생략)
    4. 🌟드라이브 폴더 최우선 안내🌟:
       - 실시간 학교 자료 목록에 관련된 파일명이 있다면: "💡 질문한 내용은 구글 드라이브에 **[관련 파일명]**(으)로 올라와 있어! 화면 위쪽의 '학교안내자료 모음' 단추를 눌러서 확인해 봐~" 라고 안내하십시오.
    5. 일반 질문 답변: 드라이브 안내 목록에 없다면, 함께 제공된 학교 공식 문서를 바탕으로 친절하게 답변해 주십시오. 
    6. 🚨모를 때의 대처🚨: 자료에도 없고 시트에도 없다면, 절대 지어내지 말고 "제가 가진 자료에는 그 내용이 없네요 ㅠㅠ 선생님께 직접 여쭤보는 건 어때?" 라고 대답하십시오.
    7. 🚨출력 형식 주의🚨: 시간이나 범위 등을 나타낼 때 절대 물결표(~) 기호를 사용하지 마십시오. 대신 하이픈(-)이나 한글(부터 ~ 까지)을 사용하십시오.
    """
    
    with st.chat_message("assistant"):
        try:
            try:
                school_data_df = conn.read(worksheet="학교자료", ttl=600).dropna(how='all')
                sheet_context = "\n\n[선생님이 방금 추가한 실시간 학교 자료]\n"
                for _, row in school_data_df.iterrows():
                    sheet_context += f"- {row['구분']}: {row['내용']}\n"
            except:
                sheet_context = "" 

            prompt_query = f"{recent_context}\n\n[학생의 방금 전 대답(현재 질문)]: {user_question}{sheet_context}"
            prompt_parts = [system_prompt, prompt_query]
            
            if selected_file_parts:
                prompt_parts.extend(selected_file_parts)

            response = model.generate_content(prompt_parts, stream=True)
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
