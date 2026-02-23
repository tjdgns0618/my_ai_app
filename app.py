import streamlit as st
import os
from markitdown import MarkItDown
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

# 1. 초기 설정
load_dotenv()
md = MarkItDown()

st.set_page_config(page_title="Gemini 문서 비서", layout="wide")

# UI 디자인
st.title("🤖 Gemini 파일 분석 비서")
st.markdown("""
이 앱은 **PDF, Excel, Word, TXT** 파일을 분석하여 질문에 답해줍니다. 
[Google AI Studio](https://aistudio.google.com/)에서 발급받은 API 키를 사용하세요.
""")

# 2. 사이드바 설정 (API 키 및 파일 업로드)
with st.sidebar:
    st.header("⚙️ 설정")
    google_api_key = st.text_input("Gemini API Key 입력", type="password")
    uploaded_file = st.file_uploader("파일 업로드", type=['pdf', 'xlsx', 'docx', 'txt'])
    
    st.divider()
    st.info("Tip: HWP 파일은 PDF로 저장해서 올려주세요.")

# 3. 메인 로직
if uploaded_file and google_api_key:
    # 파일을 임시로 로컬에 저장
    temp_path = f"temp_{uploaded_file.name}"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    try:
        # 파일 내용 추출 (MarkItDown 활용)
        with st.status("파일 읽는 중...", expanded=True) as status:
            result = md.convert(temp_path)
            content = result.text_content
            status.update(label="파일 변환 완료!", state="complete", expanded=False)

        # 추출된 내용 미리보기
        with st.expander("📄 추출된 텍스트 내용 확인"):
            st.text_area("파일 본문", content, height=250)

        # 4. 질문 및 답변 영역
        st.subheader("💬 문서에 대해 질문하세요")
        user_question = st.text_input("예시: 이 문서의 핵심 내용을 요약해줘.")

        if user_question:
            with st.spinner("Gemini가 생각 중입니다..."):
                # Gemini 모델 설정
                llm = ChatGoogleGenerativeAI(
                    model="gemini-3-flash-preview", 
                    google_api_key=google_api_key,
                    temperature=0.1 # 답변의 일관성을 위해 낮게 설정
                )
                
                # 프롬프트 구성 (문서 내용 주입)
                full_prompt = f"""
                당신은 문서 분석 전문가입니다. 아래 제공된 문서 내용을 바탕으로 사용자의 질문에 친절하고 정확하게 답하세요.
                내용이 문서에 없다면 모른다고 답하세요.

                [문서 내용]
                {content}

                [사용자 질문]
                {user_question}
                """
                
                response = llm.invoke(full_prompt)
                
                # 답변 내용만 안전하게 추출
                if hasattr(response, 'content'):
                    final_answer = response.content
                else:
                    final_answer = str(response)

                # 결과 출력
                st.write("---")
                st.markdown("### 📢 AI 답변")

                # 만약 출력값이 여전히 [{'type': 'text', ...}] 형태라면 텍스트만 골라냄
                if isinstance(final_answer, list) and len(final_answer) > 0:
                    if isinstance(final_answer[0], dict) and 'text' in final_answer[0]:
                        final_answer = final_answer[0]['text']

                st.success(final_answer)

    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")
    
    finally:
        # 작업이 끝나면 임시 파일 삭제
        if os.path.exists(temp_path):
            os.remove(temp_path)
else:
    if not google_api_key:
        st.warning("사이드바에 Gemini API Key를 입력해주세요.")
    elif not uploaded_file:
        st.info("분석할 파일을 업로드해주세요.")