import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup

from langchain.vectorstores import FAISS
from langchain.text_splitter import CharacterTextSplitter
from langchain.docstore.document import Document
from langchain.chains import RetrievalQA
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI

load_dotenv()

# Load all Gemini API keys
GEMINI_KEYS = [
    os.getenv("GOOGLE_API_KEY_1"),
    os.getenv("GOOGLE_API_KEY_2"),
    os.getenv("GOOGLE_API_KEY_3"),
    os.getenv("GOOGLE_API_KEY_4"),
    os.getenv("GOOGLE_API_KEY_5"),
    os.getenv("GOOGLE_API_KEY_6"),
    os.getenv("GOOGLE_API_KEY_7"),
]

def get_working_embedding():
    for key in GEMINI_KEYS:
        if not key:
            continue
        try:
            return GoogleGenerativeAIEmbeddings(
                model="models/embedding-001",
                google_api_key=key
            )
        except Exception:
            continue
    raise RuntimeError("⚠️ All embedding keys failed.")

def get_working_llm():
    for key in GEMINI_KEYS:
        if not key:
            continue
        try:
            return ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=key
            )
        except Exception:
            continue
    raise RuntimeError("⚠️ All LLM keys failed.")

def store_notes_as_vectors(html_text: str, user_id: str):
    """
    Converts HTML notes into embeddings and stores FAISS vectorstore
    in a temporary path based on user ID.
    """
    soup = BeautifulSoup(html_text, "html.parser")
    clean_text = soup.get_text(separator="\n")

    splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs = splitter.split_documents([Document(page_content=clean_text)])

    vector_path = f"/tmp/vectorstore_user_{user_id}"
    os.makedirs(vector_path, exist_ok=True)

    embeddings = get_working_embedding()
    db = FAISS.from_documents(docs, embeddings)
    db.save_local(vector_path)

def ask_question_with_rag(user_id: str, question: str) -> str:
    """
    Loads FAISS vectorstore for a given user ID, runs RAG using Gemini.
    """
    vector_path = f"/tmp/vectorstore_user_{user_id}"
    if not os.path.exists(os.path.join(vector_path, "index.faiss")):
        return "⚠️ No notes found. Please upload notes first."

    embeddings = get_working_embedding()
    db = FAISS.load_local(vector_path, embeddings, allow_dangerous_deserialization=True)
    retriever = db.as_retriever()

    llm = get_working_llm()
    qa = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)

    return qa.run(question)





