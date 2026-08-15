import sys
import os
import re
import json
import shutil
import logging
from pathlib import Path
from pydantic import BaseModel
from fastapi import FastAPI, Request, UploadFile, File, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# ---------------------------------------------------------------------------
# Setup PATH and Logging
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"

for p in (PROJECT_ROOT, SRC):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from resume_mod.config import get_settings
from resume_mod.runner import run_pipeline
from resume_mod.logger.logger import Logger

# Initialize application-wide logging
Logger()
LOGGER = logging.getLogger("resume_mod.web")

app = FastAPI(title="ResumeAI - AI Resume Tailoring")

# Mount Static Files and Templates
app.mount("/static", StaticFiles(directory=str(PROJECT_ROOT / "web" / "static")), name="static")
templates = Jinja2Templates(directory=str(PROJECT_ROOT / "web" / "templates"))

STATE_FILE = PROJECT_ROOT / "web" / "state.json"

# ---------------------------------------------------------------------------
# Helper State Functions
# ---------------------------------------------------------------------------
def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            LOGGER.error("Failed to load state.json: %s", e)
            return {}
    return {}

def save_state(active_resume: str | None):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(STATE_FILE, "w") as f:
            json.dump({"active_resume": active_resume}, f)
    except Exception as e:
        LOGGER.error("Failed to save state.json: %s", e)

def reindex_active_resume(active_filename: str):
    """
    Clears the ChromaDB store and re-indexes only the active base resume.
    Temporarily moves all other files in data/documents/ out of the way,
    then runs the existing ingest_documents() code, then restores the files.
    """
    settings = get_settings()
    docs_dir = settings.documents_dir
    chroma_dir = settings.chroma_dir
    temp_dir = docs_dir.parent / "temp_inactive_docs"

    active_path = docs_dir / active_filename
    if not active_path.exists():
        raise FileNotFoundError(f"Active resume {active_filename} not found.")

    LOGGER.info("Starting re-indexing for active resume: %s", active_filename)

    # 1. Identify and move all other files out of documents directory
    temp_dir.mkdir(parents=True, exist_ok=True)
    moved_files = []
    try:
        for p in docs_dir.iterdir():
            if p.is_file() and p.name != active_filename:
                # Only check supported formats in documents dir
                if p.suffix.lower() in {".pdf", ".txt", ".md", ".docx"}:
                    target = temp_dir / p.name
                    LOGGER.info("Temporarily moving %s to %s", p.name, target)
                    shutil.move(str(p), str(target))
                    moved_files.append((target, p))

        # 2. Clear Chroma DB persist folder contents
        if chroma_dir.exists():
            LOGGER.info("Clearing ChromaDB persist folder: %s", chroma_dir)
            shutil.rmtree(chroma_dir)
            chroma_dir.mkdir(parents=True, exist_ok=True)

        # 3. Call existing ingestion pipeline
        from resume_mod.ingestion.ingestion import ingest_documents
        ingest_documents()
        LOGGER.info("Ingestion completed successfully for active resume.")
    finally:
        # 4. Restore files back to the documents folder
        for src, dest in moved_files:
            if src.exists():
                LOGGER.info("Restoring file %s to %s", src.name, dest)
                shutil.move(str(src), str(dest))
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------
@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse(request, "index.html", {})

@app.get("/api/status")
def get_status():
    settings = get_settings()
    docs_dir = settings.documents_dir

    supported_exts = {".pdf", ".txt", ".md", ".docx"}
    files = []
    if docs_dir.exists():
        files = sorted(
            p.name for p in docs_dir.iterdir()
            if p.is_file() and p.suffix.lower() in supported_exts
        )

    state = load_state()
    active_resume = state.get("active_resume")

    # If active resume is not set or not present in available files,
    # default to the first one available
    if files:
        if not active_resume or active_resume not in files:
            active_resume = files[0]
            save_state(active_resume)
            try:
                reindex_active_resume(active_resume)
            except Exception as e:
                LOGGER.exception("Failed to automatically reindex default resume: %s", e)
    else:
        active_resume = None
        save_state(None)

    return {
        "success": True,
        "has_base_resume": active_resume is not None,
        "active_resume": active_resume,
        "available_resumes": files
    }

@app.post("/api/resume/upload")
async def upload_resume(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext != ".pdf":
        return {"success": False, "error": "Only PDF files are allowed."}

    # Sanitize file name
    safe_name = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", file.filename)
    if not safe_name:
        safe_name = "uploaded_resume.pdf"

    settings = get_settings()
    dest_path = settings.documents_dir / safe_name

    # Enforce size limit (10MB)
    max_size = 10 * 1024 * 1024
    size = 0
    try:
        settings.documents_dir.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "wb") as f:
            while chunk := await file.read(8192):
                size += len(chunk)
                if size > max_size:
                    f.close()
                    dest_path.unlink(missing_ok=True)
                    return {"success": False, "error": "File size exceeds limit of 10MB."}
                f.write(chunk)
    except Exception as e:
        LOGGER.exception("Failed to write uploaded file to disk.")
        return {"success": False, "error": f"Failed to save file: {str(e)}"}

    # Reindex ChromaDB for this resume and save state
    try:
        reindex_active_resume(safe_name)
        save_state(safe_name)
    except Exception as e:
        LOGGER.exception("Failed to reindex uploaded resume.")
        return {"success": False, "error": f"Failed to process and index resume: {str(e)}"}

    return {
        "success": True,
        "active_resume": safe_name
    }

class ChangeResumeRequest(BaseModel):
    filename: str

@app.post("/api/resume/change")
def change_resume(request: ChangeResumeRequest):
    filename = request.filename
    if not filename or ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename format")

    settings = get_settings()
    target_path = settings.documents_dir / filename
    if not target_path.exists() or not target_path.is_file():
        return {"success": False, "error": f"Resume {filename} not found."}

    try:
        reindex_active_resume(filename)
        save_state(filename)
    except Exception as e:
        LOGGER.exception("Failed to switch resume.")
        return {"success": False, "error": f"Failed to index resume: {str(e)}"}

    return {
        "success": True,
        "active_resume": filename
    }

class GenerateRequest(BaseModel):
    job_description: str

@app.post("/api/generate")
def generate_resume(request: GenerateRequest):
    jd = request.job_description
    if not jd or not jd.strip():
        return {"success": False, "error": "Job description must not be empty."}

    state = load_state()
    active_resume = state.get("active_resume")

    settings = get_settings()
    if not active_resume or not (settings.documents_dir / active_resume).exists():
        return {"success": False, "error": "Base resume must be uploaded first."}

    try:
        LOGGER.info("Starting pipeline generation for job description.")
        # Trigger existing pipeline
        output_path = run_pipeline(
            job_description=jd,
            retrieval_k=8,
            use_queue=False
        )
        filename = Path(output_path).name
        return {
            "success": True,
            "filename": filename
        }
    except Exception as e:
        LOGGER.exception("Error during resume generation pipeline.")
        return {"success": False, "error": f"Failed to generate resume: {str(e)}"}

@app.get("/api/resumes")
def get_resumes():
    settings = get_settings()
    pdf_dir = settings.data_dir / "updated_pdfs"

    if not pdf_dir.exists():
        pdf_dir.mkdir(parents=True, exist_ok=True)

    pdfs = []
    for p in pdf_dir.iterdir():
        if p.is_file() and p.suffix.lower() == ".pdf":
            mtime = p.stat().st_mtime
            from datetime import datetime
            dt = datetime.fromtimestamp(mtime)
            created_at = dt.strftime("%Y-%m-%d %H:%M:%S")

            # Parse candidate name and job title from filename
            name_parts = p.stem.split("_")
            job_title = "Tailored Resume"

            # Check for timestamp pattern (8 digits)
            ts_idx = -1
            for idx, part in enumerate(name_parts):
                if re.match(r"^\d{8}$", part):
                    ts_idx = idx
                    break

            if ts_idx > 1:
                job_title_slug = "_".join(name_parts[1:ts_idx])
                job_title = job_title_slug.replace("_", " ").title()
            else:
                job_title = p.stem.replace("_", " ").title()

            pdfs.append({
                "filename": p.name,
                "job_title": job_title,
                "created_at": created_at,
                "mtime": mtime
            })

    pdfs.sort(key=lambda x: x["mtime"], reverse=True)

    return {
        "success": True,
        "resumes": pdfs
    }

@app.get("/api/download/{filename}")
def download_resume(filename: str):
    if not filename or ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename format")

    settings = get_settings()
    pdf_dir = settings.data_dir / "updated_pdfs"
    file_path = (pdf_dir / filename).resolve()

    if not file_path.is_relative_to(pdf_dir.resolve()):
        raise HTTPException(status_code=403, detail="Access denied")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=filename
    )

# ---------------------------------------------------------------------------
# Programmatic Startup Entry Point
# ---------------------------------------------------------------------------
def main():
    import uvicorn
    uvicorn.run("web.app:app", host="127.0.0.1", port=8000, reload=True)
