import streamlit as st
import os
from markitdown import MarkItDown
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from PIL import Image # 이미지 처리를 위한 도구

# 1. 초기 설정
load_dotenv()
md = MarkItDown()

st.set_page_config(page_title="Gemini 멀티모달 비서", layout="wide")
st.title("🖼️ 문서 & 이미지 통합 분석 AI")

# 2. 사이드바 설정
with st.sidebar:
    st.header("⚙️ 설정")
    google_api_key = st.text_input("Gemini API Key 입력", type="password")
    # 이미지 파일 형식(png, jpg, jpeg) 추가
    uploaded_file = st.file_uploader("파일 업로드", type=['pdf', 'xlsx', 'docx', 'txt', 'png', 'jpg', 'jpeg'])

if uploaded_file and google_api_key:
    temp_path = f"temp_{uploaded_file.name}"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    try:
        # 파일 타입 확인
        file_ext = os.path.splitext(temp_path)[1].lower()
        
        # 이미지 파일일 경우 화면에 표시
        if file_ext in ['.png', '.jpg', '.jpeg']:
            image = Image.open(temp_path)
            st.image(image, caption="업로드된 이미지", use_container_width=True)
            content = "이것은 이미지 파일입니다. 이미지 내의 글자와 시각적 요소를 분석해 주세요."
        else:
            # 문서 파일일 경우 텍스트 추출
            with st.status("파일 읽는 중..."):
                result = md.convert(temp_path)
                content = result.text_content
            with st.expander("📄 추출된 내용 확인"):
                st.text_area("본문", content, height=200)

        # 3. 질문 및 답변 영역
        st.subheader("💬 무엇이든 물어보세요")
        user_question = st.text_input("질문 입력:")

        if user_question:
            with st.spinner("Gemini가 분석 중..."):
                llm = ChatGoogleGenerativeAI(
                    model="gemini-3-flash-preview", # 이미지 분석에 탁월한 모델
                    google_api_key=google_api_key
                )
                
                # 이미지를 함께 전달하는 방식 (멀티모달 프롬프트)
                if file_ext in ['.png', '.jpg', '.jpeg']:
                    # 이미지 파일인 경우 메시지 구성
                    from langchain_core.messages import HumanMessage
                    message = HumanMessage(
                        content=[
                            {"type": "text", "text": user_question},
                            {"type": "image_url", "image_url": temp_path}
                        ]
                    )
                    response = llm.invoke([message])
                else:
                    # 문서 파일인 경우 (기존 방식)
                    full_prompt = f"문서 내용: {content}\n\n질문: {user_question}\n답변 시 이미지에 대한 언급이 있다면 상세히 설명해줘."
                    response = llm.invoke(full_prompt)
                
                # 결과 출력 (텍스트만 깔끔하게)
                final_answer = response.content if hasattr(response, 'content') else str(response)
                st.write("---")
                st.markdown("### 📢 AI 답변")
                st.info(final_answer)

    except Exception as e:
        st.error(f"오류 발생: {e}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)