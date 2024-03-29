import os
from dotenv import load_dotenv
import openai
from openai import OpenAI
from PyPDF2 import PdfReader
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from chromadb.config import Settings


# env에서 Open API 키 가져오기
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERVER_HOST = os.getenv("SERVER_HOST")
HTTTP_PORT = os.getenv("HTTTP_PORT")
openai.api_key = OPENAI_API_KEY 


def _join(current_doc, separator):
    text = separator.join(current_doc)
    text = text.strip()
    if text == "":
        return None
    else:
        return text

def split_text(raw_text, separator, chunk_size, chunk_overlap):
    splited_texts = raw_text.split(separator)

    docs = []
    current_doc = []
    total = 0
    for d in splited_texts:
        _len = len(d)
        # PoC를 위하여 \n 으로 우선 고정
        separator_len = 2
        if (
            total + _len + (separator_len if len(current_doc) > 0 else 0)
            > chunk_size
        ):
            if total > chunk_size:
                print(
                    f"Created a chunk of size {total}, "
                    f"which is longer than the specified {chunk_size}"
                )
            if len(current_doc) > 0:
                doc = _join(current_doc, separator)
                if doc is not None:
                    docs.append(doc)
                while total > chunk_overlap or (
                    total + _len + (separator_len if len(current_doc) > 0 else 0)
                    > chunk_size
                    and total > 0
                ):
                    total -= len(current_doc[0]) + (
                        separator_len if len(current_doc) > 1 else 0
                    )
                    current_doc = current_doc[1:]
        current_doc.append(d)
        total += _len + (separator_len if len(current_doc) > 1 else 0)
    doc = _join(current_doc, separator)
    if doc is not None:
        docs.append(doc)
    return docs


def get_pdf_text(file_path):
    # pypdf 를 통해서 pdf 문서 읽기
    doc_reader = PdfReader(file_path)
    raw_text = ''
    for i, page in enumerate(doc_reader.pages):
        text = page.extract_text()
        if text:
            raw_text += text
    return raw_text

def get_text_chunks(raw_text):
    chunks = split_text(raw_text, "\n", 512, 100)
    return chunks

def get_vectorstore(text_chunks, collection_name):
    # Embedding에 사용할 Embedding 모델 생성
    EMBEDDING_MODEL = "text-embedding-ada-002"
    embeddings = OpenAIEmbeddingFunction(api_key=os.environ.get('OPENAI_API_KEY'), model_name=EMBEDDING_MODEL)

    # Vector 스토어 생성. 편의성을 위하여 ChromaDB 사용
    # local 에서 Docker 사용하여 Chroma DB 업로드 할 예정
    # Docker에서 띄워놓지 않으면 데이터가 in-memory에서 휘발됨
    client_settings = Settings(
            # chroma_api_impl="rest",
            chroma_server_host=SERVER_HOST,
            chroma_server_http_port=HTTTP_PORT
        )
    chroma_client = chromadb.HttpClient(settings=client_settings)


    collection = chroma_client.get_or_create_collection(
        name=collection_name
        ,embedding_function=embeddings
    )

    collection.add(
        documents=text_chunks,
        ids=[str(i) for i in range(len(text_chunks))]
    )

    return collection


def add_message(role, content):
    return { "role": role, "content":content }

def get_retriever_message(vectorstore, question):
    query_text = []
    query_text.append(question)
    retrieved_information = vectorstore.query(
        query_texts= query_text,
        n_results = 1
    )

    question = question

    template_prompt = f'''
        You are an intelligent assistant helping the users with their questions on the collection data. Strictly Use ONLY the following pieces of context to answer the question at the end. Think step-by-step and then answer.
        
        Do not try to make up an answer:
        - If the answer to the question cannot be determined from the context alone, say "I cannot determine the answer to that."
        - If the context is empty, just say "I do not know the answer to that."
        
        CONTEXT:
        {retrieved_information}
        
        QUESTION:
        {question}
    
        Helpful Answer:
    '''
    return add_message("system", template_prompt)


def get_response_from_openAI(chat_memory):
    client = OpenAI()
    return client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=chat_memory
    )

def main():

    # Embedding 할 path 선택
    current_path = os.getcwd()
    file_name = 'test.pdf'
    file_path = os.path.join(current_path, file_name)

    # Embedding 할 문서에서 Text 추출
    raw_text = get_pdf_text(file_path)

    # 문서 Embedding을 위한 Chunk 준비
    text_chunks = get_text_chunks(raw_text)

    # Embedding 시작하기
    collection_name = "my_document"
    vectorstore = get_vectorstore(text_chunks, collection_name)

    # Chat conversation을 저장하기 위하여 memory 지정
    chat_memory = []

    # User Input을 받아서 대화를 생성
    while True:
        
        user_input = input("User: ")
        # Retriever를 위한 prompt 생성
        retriever_momory = get_retriever_message(vectorstore, user_input)
        chat_memory.append(retriever_momory)
        user_memory = add_message("user", user_input)
        chat_memory.append(user_memory)

        # Retriever prompt 및 Question 전달
        response = get_response_from_openAI(chat_memory)
        chatbot_response = response.choices[0].message.content

        print("Chatbot response: " + chatbot_response)

        # assistant 대화 이력 업데이트
        chatbot_message = add_message("assistant", chatbot_response)
        chat_memory.append(chatbot_message)

if __name__ == '__main__':
    main()



