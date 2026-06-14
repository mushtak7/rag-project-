import os
import shutil
from contextlib import asynccontextmanager
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db, init_db
from models import User, ChatMessage, Document
from auth import hash_password, verify_password, create_access_token, get_current_user
from logger_config import get_logger
import rag_engine

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app):
    """Startup and shutdown events."""
    init_db()
    logger.info("Database initialized. Server is ready.")
    yield


app = FastAPI(title="AI Document Intelligence System", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure directories
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)


# ── Schemas ───────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class ChatRequest(BaseModel):
    message: str




# ── Auth Routes ───────────────────────────────────────────────
@app.post("/api/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if not req.email or not req.password:
        raise HTTPException(status_code=400, detail="Email and password are required.")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    user = User(email=req.email, password_hash=hash_password(req.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"user_id": user.id, "email": user.email})
    logger.info(f"New user registered: {req.email}")
    return {"token": token, "email": user.email}


@app.post("/api/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        logger.warning(f"Failed login attempt for: {req.email}")
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_access_token({"user_id": user.id, "email": user.email})
    logger.info(f"User logged in: {req.email}")
    return {"token": token, "email": user.email}


# ── Upload Route (Multi-PDF) ─────────────────────────────────
@app.post("/api/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    # ── Pass 1: Validate all files BEFORE writing anything to disk ──
    for file in files:
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="One of the uploaded files has no filename.",
            )
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail=f"Only PDF files are supported. '{file.filename}' is not a PDF.",
            )

    # ── Pass 2: Save validated files to disk ──
    saved_paths = []
    filenames = []

    try:
        user_upload_dir = rag_engine._user_upload_dir(current_user.id)

        for file in files:
            dest_path = os.path.join(user_upload_dir, file.filename)
            with open(dest_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            if os.path.getsize(dest_path) == 0:
                os.remove(dest_path)
                raise HTTPException(
                    status_code=400,
                    detail=f"The file '{file.filename}' is empty.",
                )

            saved_paths.append(dest_path)
            filenames.append(file.filename)

            # Track in database
            doc_record = Document(user_id=current_user.id, filename=file.filename)
            db.add(doc_record)

        db.commit()

        # Process all documents together
        result = rag_engine.process_documents(saved_paths, filenames, current_user.id)
        logger.info(f"Upload success for user {current_user.id}: {filenames}")
        return {
            "message": f"Successfully processed {len(filenames)} document(s)",
            "details": result,
        }

    except HTTPException:
        # Clean up any files written before the error
        for path in saved_paths:
            if os.path.exists(path):
                os.remove(path)
        raise
    except Exception as e:
        # Clean up any files written before the error
        for path in saved_paths:
            if os.path.exists(path):
                os.remove(path)
        logger.error(f"Upload error for user {current_user.id}: {e}")
        if "API key" in str(e) or "GEMINI" in str(e):
            raise HTTPException(status_code=500, detail="Gemini API key is missing or invalid.")
        raise HTTPException(status_code=500, detail=str(e))


# ── Chat Route (Memory-Aware) ────────────────────────────────
@app.post("/api/chat")
def chat(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        # Load recent chat history from DB
        recent_messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.user_id == current_user.id)
            .order_by(ChatMessage.created_at.desc())
            .limit(10)  # fetch last 10, engine will trim to k=5
            .all()
        )
        recent_messages.reverse()  # chronological order

        chat_history = [
            {"role": msg.role, "content": msg.content} for msg in recent_messages
        ]

        # Execute RAG query
        result = rag_engine.query_rag(req.message, current_user.id, chat_history)

        # Save this exchange to DB for future memory
        db.add(ChatMessage(user_id=current_user.id, role="human", content=req.message))
        db.add(ChatMessage(user_id=current_user.id, role="ai", content=result["answer"]))
        db.commit()

        return result

    except Exception as e:
        if "No documents uploaded" in str(e):
            raise HTTPException(status_code=400, detail=str(e))
        logger.error(f"Chat error for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Get User Documents ────────────────────────────────────────
@app.get("/api/documents")
def get_documents(current_user: User = Depends(get_current_user)):
    docs = rag_engine.get_user_documents(current_user.id)
    return {"documents": docs}


# ── Delete a Document ─────────────────────────────────────────
@app.delete("/api/documents/delete")
def delete_document(
    filename: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not filename or not filename.strip():
        raise HTTPException(status_code=400, detail="Filename is required.")
    try:
        result = rag_engine.delete_document(current_user.id, filename)

        # Remove from database
        db.query(Document).filter(
            Document.user_id == current_user.id,
            Document.filename == filename,
        ).delete()
        db.commit()

        logger.info(f"Document '{filename}' deleted for user {current_user.id}")
        return result
    except Exception as e:
        logger.error(f"Delete error for user {current_user.id}: {e}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ── Serve Uploaded PDF for Viewer ─────────────────────────────
@app.get("/api/pdf/{filename}")
def serve_pdf(filename: str, current_user: User = Depends(get_current_user)):
    user_dir = rag_engine._user_upload_dir(current_user.id)
    file_path = os.path.join(user_dir, filename)

    # Prevent path traversal attacks (e.g., filename="../../.env")
    if not os.path.realpath(file_path).startswith(os.path.realpath(user_dir)):
        raise HTTPException(status_code=400, detail="Invalid filename.")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="PDF not found.")
    return FileResponse(file_path, media_type="application/pdf")


# ── Clear Chat History ────────────────────────────────────────
@app.delete("/api/chat/clear")
def clear_chat(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(ChatMessage).filter(ChatMessage.user_id == current_user.id).delete()
    db.commit()
    logger.info(f"Chat history cleared for user {current_user.id}")
    return {"message": "Chat history cleared."}


# ── Frontend ──────────────────────────────────────────────────
@app.get("/")
def serve_index():
    return FileResponse("static/index.html")


# Mount static files LAST so API routes take priority
app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
