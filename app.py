import streamlit as st
import sys
import io  # 이 부분이 누락되면 에러가 발생합니다.
import os
import shutil
import time
import base64
import pandas as pd
import mammoth  # docx 변환용
from markitdown import MarkItDown
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv
from PIL import Image

# 0. 한글 인코딩 문제 방지를 위한 강제 설정
# 질문에 포함된 한글이 깨지거나 'ascii' 에러가 나는 것을 방지합니다.
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')

# 1. 초기 설정 및 보안
load_dotenv()
IMAGE_EXPORT_DIR = "temp_extracted_images"

if not os.path.exists(IMAGE_EXPORT_DIR):
    os.makedirs(IMAGE_EXPORT_DIR)

md = MarkItDown()

# --- 기능 함수 정의 ---

def display_pdf(file_path):
    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

def display_excel(file_path):
    df = pd.read_excel(file_path)
    st.dataframe(df, use_container_width=True, height=600)

def display_docx(file_path):
    with open(file_path, "rb") as docx_file:
        result = mammoth.convert_to_html(docx_file)
        st.markdown(f'<div style="height:800px; overflow-y:scroll; border:1px solid #ddd; padding:10px; background-color:white; color:black;">{result.value}</div>', unsafe_allow_html=True)

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# --- UI 구성 ---

st.set_page_config(page_title="Gemini 통합 분석 비서", layout="wide")
st.title("📂 스마트 문서 & 이미지 분석기")

# 2. 사이드바 설정
with st.sidebar:
    st.header("⚙️ 설정")
    google_api_key = st.text_input("Gemini API Key 입력", type="password")
    uploaded_file = st.file_uploader("파일 업로드", type=['pdf', 'png', 'jpg', 'jpeg', 'docx', 'xlsx', 'txt'])
    
    st.warning("⚠️ **HWP 파일 안내**\n\n한글(HWP) 파일은 직접 미리보기가 어렵습니다. 분석을 위해 반드시 **PDF로 변환 후** 업로드해 주세요.")
    
    st.divider()
    if st.button("이미지 캐시 삭제"):
        if os.path.exists(IMAGE_EXPORT_DIR):
            shutil.rmtree(IMAGE_EXPORT_DIR)
            os.makedirs(IMAGE_EXPORT_DIR)
        st.success("캐시가 삭제되었습니다.")

# 3. 파일 처리 및 화면 분할
if uploaded_file and google_api_key:
    temp_path = os.path.join(os.getcwd(), f"temp_{uploaded_file.name}")
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    col1, col2 = st.columns([1, 1])
    file_ext = os.path.splitext(temp_path)[1].lower()

    # --- 왼쪽: 원본 파일 미리보기 ---
    with col1:
        st.subheader("📄 원본 파일 보기")
        try:
            if file_ext == '.pdf':
                display_pdf(temp_path)
            elif file_ext in ['.png', '.jpg', '.jpeg']:
                st.image(temp_path, use_container_width=True)
            elif file_ext in ['.xlsx', '.xls']:
                display_excel(temp_path)
            elif file_ext == '.docx':
                display_docx(temp_path)
            elif file_ext == '.txt':
                with open(temp_path, 'r', encoding='utf-8') as f:
                    st.text_area("텍스트 내용", f.read(), height=600)
            else:
                st.info("이 형식은 미리보기를 지원하지 않지만, 분석은 가능합니다.")
        except Exception as e:
            st.error(f"미리보기 로드 실패: {e}")

    # --- 오른쪽: AI 채팅 및 분석 ---
    with col2:
        st.subheader("🤖 AI와 대화하기")
        
        try:
            with st.spinner("내용 분석 중..."):
                file_image_dir = os.path.join(IMAGE_EXPORT_DIR, str(int(time.time())))
                os.makedirs(file_image_dir, exist_ok=True)
                result = md.convert(temp_path, image_extractor_output_dir=file_image_dir)
                content = result.text_content
                time.sleep(1) 

            user_question = st.text_input("문서의 내용이나 수치에 대해 물어보세요:")

            if user_question:
                with st.spinner("Gemini가 생각 중..."):
                    llm = ChatGoogleGenerativeAI(
                        model="gemini-3-flash-preview", # 안정적인 분석을 위해 1.5 flash 권장
                        google_api_key=google_api_key,
                        temperature=0
                    )
                    
                    if file_ext in ['.png', '.jpg', '.jpeg']:
                        b64_img = encode_image(temp_path)
                        message = HumanMessage(content=[
                            {"type": "text", "text": f"이 이미지의 텍스트와 숫자를 정확히 분석해줘. 질문: {user_question}"},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
                        ])
                        response = llm.invoke([message])
                    else:
                        full_prompt = f"문서 내용:\n{content}\n\n질문: {user_question}\n수치나 표 데이터를 정확히 확인해서 답변해줘."
                        response = llm.invoke(full_prompt)
                    
                    answer = response.content if hasattr(response, 'content') else str(response)
                    st.write("---")
                    st.markdown("### 📢 AI 답변")
                    st.success(answer)

        except Exception as e:
            # 에러 메시지도 유니코드(한글) 처리를 위해 str()로 감쌉니다.
            st.error(f"분석 중 오류 발생: {str(e)}")
else:
    st.info("사이드바에서 Gemini API 키를 입력하고 파일을 업로드해 주세요.")