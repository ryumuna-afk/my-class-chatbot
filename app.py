if user_question := st.chat_input("질문을 입력하세요!"):
    
    with st.chat_message("user"):
        st.write(user_question)
        
    recent_context = ""
    if not my_records.empty:
        recent_context = "[이전 대화 맥락]\n"
        for _, row in my_records.tail(3).iterrows():
            recent_context += f"학생: {row['질문내용']}\n비서: {row['AI답변']}\n"

    # [요금 절감 1단계] 사서 AI
    selected_file_parts = []
    if global_school_files:
        file_names_str = ", ".join(global_school_files.keys())
        router_prompt = f"""
        학생 질문: "{user_question}"
        이전 대화 맥락: "{recent_context}"
        학교 보유 파일 목록: [{file_names_str}]
        
        당신은 자료 분류 사서입니다. 위 학생의 질문에 대답하기 위해 꼭 확인해야 할 파일의 이름을 '학교 보유 파일 목록'에서 유추하여 골라주세요.
        답변 규칙: 파일 이름만 쉼표(,)로 구분해서 적고, 관련 파일이 전혀 없으면 반드시 '없음'이라고만 적어주세요.
        """
        try:
            router_response = model.generate_content(router_prompt)
            router_answer = router_response.text
            
            for fname, fcontent in global_school_files.items():
                if fname in router_answer:
                    selected_file_parts.append(fcontent)
        except:
            pass
        
    # 🌟 [문제 해결] 모르면 당당하게 모른다고 말하는 강력한 프롬프트 적용
    system_prompt = f"""
    당신은 고등학교 진로 상담 비서입니다. (선택된 페르소나: {persona})

    [행동 수칙]
    1. 🚨주제 이탈 금지🚨: 학교생활, 진로, 상급학년 준비와 무관한 질문은 단호하게 거절하십시오.
    2. 문서 기반 답변: 질문에 부합한다면, 함께 전달된 [학교 공식 원본 문서들]만 분석하여 정답을 찾으십시오.
    3. 🚨모를 땐 당당하게 모른다고 하기 (매우 중요)🚨: 만약 전달된 학교 문서에 질문에 대한 답이 없다면, 절대 이전 대화 내용(예: 8시 10분 등교 등)을 엉뚱하게 끌어오거나 지어내지 마십시오!! 반드시 "제가 가진 학교 자료에는 관련 내용이 없네요 ㅠㅠ 정확한 건 선생님께 꼭 확인해 보세요!"라고만 대답하십시오.
    4. 말투 지시: "문서에 따르면" 같은 기계적인 출처 언급 없이, 원래 알았던 것처럼 페르소나에 맞춰 자연스럽게 말하십시오.
    5. 출력 형식: 시간/범위 등을 나타낼 때 절대 물결표(~) 기호를 사용하지 마십시오. 하이픈(-)이나 한글(부터 ~ 까지)을 사용하십시오.
    """
    
    with st.chat_message("assistant"):
        try:
            # [요금 절감 2단계] 진짜 답변 생성
            prompt_query = f"{recent_context}\n\n[현재 학생의 질문]: {user_question}"
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
