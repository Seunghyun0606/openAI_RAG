import os
from dotenv import load_dotenv
import openai
from openai import OpenAI
from PYPDF2 import PdfReader

# env에서 Open API 키 가져오기
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY 

def get_pdf_text(file_path):
    # pypdf 를 통해서 pdf 문서 읽기
    doc_reader = PdfReader(file_path)
    raw_text = ''
    for i, page in enumerate(doc_reader.pages):
        text = page.extract_text()
        if text:
            raw_text += text
    return raw_text


def main():

    # Embedding 할 path 선택
    current_path = os.getcwd()
    file_name = 'test.pdf'
    file_path = os.path.join(current_path, file_name)

    # Embedding 할 문서에서 Text 추출
    raw_text = get_pdf_text(file_path)


if __name__ == '__main__':
    main()



