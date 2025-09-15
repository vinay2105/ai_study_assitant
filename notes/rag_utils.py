import os
from bs4 import BeautifulSoup
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import CharacterTextSplitter
from langchain.docstore.document import Document
from langchain.chains import RetrievalQA
from langchain.embeddings import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI

# -----------------------------
# Hugging Face Embeddings Model
# -----------------------------
def get_hf_embeddings():
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# -----------------------------
# Gemini LLM (for generating / answering)
# -----------------------------
def get_working_llm():
    gemini_key = os.getenv("GOOGLE_API_KEY_1")  # single key for simplicity
    if not gemini_key:
        raise RuntimeError("⚠️ No Gemini API key found.")
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=gemini_key
    )

# -----------------------------
# Store Notes as Vectors (from raw text)
# -----------------------------
def store_notes_as_vectors(raw_text: str, user_id: str):
    """
    Converts raw text into embeddings and stores FAISS vectorstore
    in a temporary path based on user ID.
    """
    splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs = splitter.split_documents([Document(page_content=raw_text)])

    vector_path = f"/tmp/vectorstore_user_{user_id}"
    os.makedirs(vector_path, exist_ok=True)

    embeddings = get_hf_embeddings()
    db = FAISS.from_documents(docs, embeddings)
    db.save_local(vector_path)

# -----------------------------
# Ask Question with RAG
# -----------------------------
def ask_question_with_rag(user_id: str, question: str) -> str:
    """
    Loads FAISS vectorstore for a given user ID and runs RAG using Gemini LLM.
    """
    vector_path = f"/tmp/vectorstore_user_{user_id}"
    if not os.path.exists(os.path.join(vector_path, "index.faiss")):
        return "⚠️ No notes found. Please upload notes first."

    embeddings = get_hf_embeddings()
    db = FAISS.load_local(vector_path, embeddings, allow_dangerous_deserialization=True)
    retriever = db.as_retriever()

    llm = get_working_llm()
    qa = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)

    return qa.run(question)










