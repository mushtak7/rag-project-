import os
import fitz  # PyMuPDF
from typing import List, Dict, Any, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from dotenv import load_dotenv
from logger_config import get_logger

load_dotenv()

logger = get_logger("rag_engine")

# ── Configuration ──────────────────────────────────────────────
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
MEMORY_LIMIT = 5  # last k exchanges kept in context
FAISS_BASE_DIR = "faiss_stores"
UPLOAD_DIR = "uploaded_pdfs"

os.makedirs(FAISS_BASE_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ── Helpers ────────────────────────────────────────────────────
def _user_faiss_dir(user_id: int) -> str:
    return os.path.join(FAISS_BASE_DIR, f"user_{user_id}")


def _user_upload_dir(user_id: int) -> str:
    path = os.path.join(UPLOAD_DIR, f"user_{user_id}")
    os.makedirs(path, exist_ok=True)
    return path


def _get_embeddings():
    return GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")


def _get_llm():
    return ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2)


# ── Text Extraction ───────────────────────────────────────────
def extract_text_from_pdf(file_path: str) -> str:
    """Extract all text from a PDF using PyMuPDF."""
    text = ""
    try:
        doc = fitz.open(file_path)
        for page in doc:
            extracted = page.get_text()
            if extracted:
                text += extracted
        doc.close()
    except Exception as e:
        logger.error(f"PDF extraction failed for {file_path}: {e}")
        raise Exception(f"Failed to extract text from PDF: {str(e)}")

    if not text.strip():
        logger.warning(f"Empty text extracted from {file_path}")
        raise Exception(
            "The PDF contains no extractable text. It may be a scanned image without OCR."
        )
    return text


# ── Document Processing (Multi-PDF) ──────────────────────────
def process_documents(file_paths: List[str], filenames: List[str], user_id: int) -> Dict[str, Any]:
    """
    Process one or more PDFs:
    1. Extract text from each
    2. Chunk with metadata tagging the source filename
    3. Embed and merge into the user's FAISS index
    4. Persist to disk
    """
    logger.info(f"Processing {len(file_paths)} document(s) for user {user_id}")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        is_separator_regex=False,
    )

    all_docs: List[Document] = []
    stats = {}

    for path, fname in zip(file_paths, filenames):
        raw_text = extract_text_from_pdf(path)
        chunks = text_splitter.split_text(raw_text)
        # Tag every chunk with its source filename
        docs = [
            Document(page_content=chunk, metadata={"source": fname})
            for chunk in chunks
        ]
        all_docs.extend(docs)
        stats[fname] = len(chunks)
        logger.info(f"  {fname}: {len(chunks)} chunks created")

    if not all_docs:
        raise Exception("No text chunks were generated from the uploaded documents.")

    embeddings = _get_embeddings()
    faiss_dir = _user_faiss_dir(user_id)

    # Merge into existing index or create new
    if os.path.exists(faiss_dir):
        logger.info(f"Merging into existing FAISS index for user {user_id}")
        existing_db = FAISS.load_local(faiss_dir, embeddings, allow_dangerous_deserialization=True)
        new_db = FAISS.from_documents(all_docs, embeddings)
        existing_db.merge_from(new_db)
        existing_db.save_local(faiss_dir)
    else:
        logger.info(f"Creating new FAISS index for user {user_id}")
        db = FAISS.from_documents(all_docs, embeddings)
        db.save_local(faiss_dir)

    total_chunks = sum(stats.values())
    logger.info(f"Total {total_chunks} chunks indexed for user {user_id}")
    return {"total_chunks": total_chunks, "per_file": stats}


# ── Query with Memory ────────────────────────────────────────
def query_rag(question: str, user_id: int, chat_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    """
    1. Load user's FAISS index
    2. Similarity search for top-k chunks
    3. Build a prompt with the last MEMORY_LIMIT exchanges
    4. Call the LLM
    5. Return the answer + source attributions
    """
    faiss_dir = _user_faiss_dir(user_id)

    if not os.path.exists(faiss_dir):
        raise Exception("No documents uploaded yet. Please upload a PDF first.")

    embeddings = _get_embeddings()
    try:
        db = FAISS.load_local(faiss_dir, embeddings, allow_dangerous_deserialization=True)
    except Exception as e:
        logger.error(f"Failed to load FAISS index for user {user_id}: {e}")
        raise Exception(f"Failed to load document index: {e}")

    # MMR search: fetches more candidates, then selects for both relevance AND diversity
    # This ensures chunks from multiple documents are included in the results
    docs = db.max_marginal_relevance_search(question, k=6, fetch_k=20, lambda_mult=0.6)

    if not docs:
        logger.info(f"No relevant chunks found for query: {question[:80]}...")
        return {
            "answer": "I couldn't find any relevant information in your uploaded documents to answer this question.",
            "sources": [],
        }

    # Build context with source labels
    context_parts = []
    for i, doc in enumerate(docs):
        source = doc.metadata.get("source", "Unknown")
        context_parts.append(f"[Source: {source}]\n{doc.page_content}")
    context = "\n\n---\n\n".join(context_parts)

    # Build memory string from last k exchanges
    memory_str = ""
    if chat_history:
        recent = chat_history[-MEMORY_LIMIT:]
        memory_lines = []
        for msg in recent:
            role = "User" if msg["role"] == "human" else "Assistant"
            memory_lines.append(f"{role}: {msg['content']}")
        memory_str = "\n".join(memory_lines)

    # Prompt
    llm = _get_llm()
    prompt = ChatPromptTemplate.from_template(
        "You are DocIntel, an enterprise AI Document Intelligence assistant.\n"
        "Answer the question using ONLY the provided document context below.\n"
        "If the answer cannot be found in the context, say so clearly.\n"
        "When citing information, mention which source document it came from.\n\n"
        "{memory_section}"
        "─── Document Context ───\n{context}\n\n"
        "─── User Question ───\n{question}\n\n"
        "Answer:"
    )

    memory_section = ""
    if memory_str:
        memory_section = f"─── Recent Conversation ───\n{memory_str}\n\n"

    chain = prompt | llm
    response = chain.invoke({
        "context": context,
        "question": question,
        "memory_section": memory_section,
    })

    logger.info(f"Query answered for user {user_id}: {question[:80]}...")

    # Build source attributions with per-document grouping
    sources = []
    for doc in docs:
        sources.append({
            "filename": doc.metadata.get("source", "Unknown"),
            "text": doc.page_content,
        })

    return {
        "answer": response.content,
        "sources": sources,
    }


# ── Get User's Uploaded Documents ─────────────────────────────
def get_user_documents(user_id: int) -> List[str]:
    """Return list of PDF filenames uploaded by this user."""
    upload_dir = _user_upload_dir(user_id)
    if not os.path.exists(upload_dir):
        return []
    return [f for f in os.listdir(upload_dir) if f.lower().endswith(".pdf")]


# ── Delete a User Document ────────────────────────────────────
def delete_document(user_id: int, filename: str) -> Dict[str, Any]:
    """
    Delete a single PDF for a user:
    1. Remove the file from disk
    2. Rebuild the FAISS index from the remaining documents
    """
    upload_dir = _user_upload_dir(user_id)
    file_path = os.path.join(upload_dir, filename)

    # Security: prevent path traversal
    if not os.path.realpath(file_path).startswith(os.path.realpath(upload_dir)):
        raise Exception("Invalid filename.")

    if not os.path.exists(file_path):
        raise Exception(f"File '{filename}' not found.")

    # 1. Remove the PDF from disk
    os.remove(file_path)
    logger.info(f"Deleted file {filename} for user {user_id}")

    # 2. Rebuild the FAISS index from remaining documents
    remaining_files = get_user_documents(user_id)
    faiss_dir = _user_faiss_dir(user_id)

    if not remaining_files:
        # No documents left — remove the entire FAISS index
        if os.path.exists(faiss_dir):
            import shutil
            shutil.rmtree(faiss_dir)
            logger.info(f"Removed FAISS index for user {user_id} (no documents left)")
        return {"remaining": 0, "message": "Document deleted. No documents remaining."}

    # Re-index all remaining documents
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        is_separator_regex=False,
    )

    all_docs: List[Document] = []
    for fname in remaining_files:
        fpath = os.path.join(upload_dir, fname)
        try:
            raw_text = extract_text_from_pdf(fpath)
            chunks = text_splitter.split_text(raw_text)
            docs = [
                Document(page_content=chunk, metadata={"source": fname})
                for chunk in chunks
            ]
            all_docs.extend(docs)
        except Exception as e:
            logger.warning(f"Skipped re-indexing {fname}: {e}")

    if all_docs:
        embeddings = _get_embeddings()
        db = FAISS.from_documents(all_docs, embeddings)
        db.save_local(faiss_dir)
        logger.info(f"Rebuilt FAISS index for user {user_id} with {len(all_docs)} chunks")
    elif os.path.exists(faiss_dir):
        import shutil
        shutil.rmtree(faiss_dir)

    return {"remaining": len(remaining_files), "message": f"Document '{filename}' deleted successfully."}
