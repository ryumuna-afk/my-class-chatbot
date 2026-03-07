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

# 표 인식과 사진 분석에 가장 강력한 2.0 엔진 사용
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.0-flash') 
conn = st.connection("gsheets", type=GSheetsConnection)

# ==========================================
# 2. 🌟 학교 공식 자료 자동 로드 (PDF, 엑셀, 이미지 모두 지원)
# ==========================================
@st.cache_data
def load_global_files():
    file_parts = []
    # 깃허브(또는 로컬)에 있는 파일 중 아래 확장자만 골라서 읽음
    valid_extensions = (".pdf", ".xlsx", ".xls", ".csv", ".png", ".jpg", ".jpeg")
    target_files = [f for f in os.listdir(".") if f.lower().endswith(valid_extensions)]
    
    for file_name in target_files:
        try:
            lower_name = file_name.lower()
            
            # 1. PDF 파일 처리 (Vision 스캔용 바이너리)
            if lower_name.endswith(".pdf"):
                with open(file_name, "rb") as f:
                    file_parts.append({
                        "mime_type": "application/pdf",
                        "data": f.read()
                    })
                    
            # 2. 엑셀/CSV 파일 처리 (텍스트 표로 자동 변환)
            elif lower_name.endswith((".xlsx", ".xls", ".csv")):
                if lower_name.endswith(".csv"):
                    df_file = pd.read_csv(file_name)
                else:
                    df_file = pd.read_excel(file_name)
                excel_text = f"\n--- [학교 엑셀/CSV 자료: {file_name}] ---\n{df_file.to_csv(index=False)}\n"
                file_parts.append(excel_text)
                
            # 3. 🌟 이미지 파일 처리 (Vision 스캔용 바이너리)
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

# 앱이 켜질 때 폴더 안의 모든 파일을 읽어들임
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
# 4. 🎨 UI 영역 1: 사이드바 (교사 전용 메뉴)
# ==========================================
with st.sidebar:
    st.markdown("### 🔐 교사용 관리 메뉴")
    st.caption("공식 학교 자료 업로드 및 문의 확인")
    
    if st.text_input("비밀번호 입력", type="password") == "0486":
        # 깃허브에 직접 올렸을 때 누르는 버튼
        if st.button("🔄 깃허브 데이터 동기화 (캐시 초기화)"):
            load_global_files.clear() 
            st.success("동기화 완료! 새 파일을 인식합니다.")
            st.rerun() 
            
        # 앱에서 바로 올리는 위젯
        file = st.file_uploader("새 학교 자료 업로드", type=["pdf", "xlsx", "xls", "csv", "png", "jpg", "jpeg"])
        if file:
            with open(file.name, "wb") as f: 
                f.write(file.getbuffer())
            load_global_files.clear()
            st.success(f"'{file.name}' 업데이트 완료!")
            
        st.markdown("---")
        st.markdown("#### 📋 접수된 학생 문의 확인")
        # 선생님이 학생들의 문의를 확인할 수 있는 영역
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
    topic = st.selectbox("📌 상담 주제", ["① 학교생활 적응", "② 진로 탐색", "③ 상급학년 준비"])

if topic == "① 학교생활 적응":
    st.info("📘 **[학교생활 적응]** 학사 일정, 생활 규정, 동아리/봉사활동 관련 정보를 물어보세요.")
elif topic == "② 진로 탐색":
    st.info("🔍 **[진로 탐색]** 직업/학과 가이드, 추천 도서, 진로 설계 사례를 물어보세요.")
elif topic == "③ 상급학년 준비":
    st.info("🎯 **[상급학년 준비]** 선택과목 특징, 전공별 권장 과목 조합을 물어보세요.")

# 🌟 사이드바에서 메인 화면으로 이동한 '선생님께 문의 남기기' 기능
with st.expander("📬 AI 비서가 아닌, 선생님께 직접 문의 남기기"):
    st.caption("진로 상담 예약이나 선생님께 직접 물어보고 싶은 내용을 적어주세요.")
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

# 대화 기록 로드 및 변수 저장
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
# 6. 💬 채팅 처리
# ==========================================
if user_question := st.chat_input("질문을 입력하세요!"):
    
    with st.chat_message("user"):
        st.write(user_question)
        
    # 이전 대화 3턴 기억하여 문맥 구성
    recent_context = ""
    if not my_records.empty:
        recent_context = "[이전 대화 맥락]\n"
        for _, row in my_records.tail(3).iterrows():
            recent_context += f"학생: {row['질문내용']}\n비서: {row['AI답변']}\n"
        
    system_prompt = f"""
    당신은 고등학교 진로 상담 비서입니다. (선택된 페르소나: {persona})

    [행동 수칙]
    1. 🚨주제 이탈 금지🚨: 만약 학생의 질문이 '학교생활 적응', '진로 탐색', '상급학년 준비' 이 3가지 주제와 전혀 관련 없는 엉뚱한 내용(예: 게임, 연예인, 일상 잡담 등)이라면, 절대 답변을 생성하지 말고 오직 다음 문장만 출력하십시오: "해당 질문은 제미나이 비서가 답변할 수 없는 주제입니다. 학교생활, 진로, 상급학년 준비와 관련된 질문을 남겨주세요!"
    2. 질문이 위 3가지 주제에 부합한다면, 함께 전달된 [학교 공식 원본 문서들(PDF/엑셀/이미지)]을 시각적으로 꼼꼼히 분석하여 정답을 찾으십시오. 특히 표나 이미지 데이터는 행과 열을 세밀하게 읽어야 합니다.
    3. 아래에 [이전 대화 맥락]이 제공되었다면, 현재 학생의 질문이 짧더라도 이전 대화와 연결되는 '꼬리 질문'인지 파악하고 문맥에 맞게 답변하십시오.
    4. 데이터에 명확한 답이 없다면 일반 지식으로 답변하되, 반드시 마지막에 "이는 일반적인 내용이므로, 정확한 내용은 학교나 선생님께 꼭 다시 확인해 봐!"라는 안내 멘트를 덧붙이십시오.
    """
    
    with st.chat_message("assistant"):
        try:
            prompt_query = f"{recent_context}\n\n[현재 학생의 질문]: {user_question}"
            prompt_parts = [system_prompt, prompt_query]
            
            if global_school_files:
                prompt_parts.extend(global_school_files)

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
