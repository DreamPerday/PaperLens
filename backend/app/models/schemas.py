from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class ProjectStatus(str, Enum):
    active = "active"
    archived = "archived"

class Project(BaseModel):
    id: str
    name: str
    description: str = ""
    status: ProjectStatus = ProjectStatus.active
    created_at: str = ""
    updated_at: str = ""
    file_count: int = 0
    total_tokens: int = 0

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = ""

class DocumentType(str, Enum):
    pdf = "pdf"
    docx = "docx"
    markdown = "markdown"
    latex = "latex"
    tex = "latex"
    txt = "txt"
    html = "html"

class DocumentInfo(BaseModel):
    id: str
    project_id: str
    filename: str
    original_name: str
    doc_type: DocumentType
    size: int
    status: str = "uploaded"
    page_count: int = 0
    created_at: str = ""
    updated_at: str = ""

class TranslationStatus(str, Enum):
    pending = "pending"
    translating = "translating"
    completed = "completed"
    failed = "failed"

class Translation(BaseModel):
    id: str
    document_id: str
    project_id: str
    source_lang: str = "en"
    target_lang: str = "zh"
    status: TranslationStatus = TranslationStatus.pending
    progress: float = 0.0
    tokens_used: int = 0
    cost_estimate: float = 0.0
    content: str = ""
    created_at: str = ""
    completed_at: str = ""

class TranslationRequest(BaseModel):
    document_id: str
    source_lang: str = "en"
    target_lang: str = "zh"

class FileUploadResponse(BaseModel):
    id: str
    filename: str
    size: int
    doc_type: DocumentType
    message: str = ""

class ProgressUpdate(BaseModel):
    document_id: str
    status: TranslationStatus
    progress: float
    tokens_used: int = 0

class TermEntry(BaseModel):
    source: str
    target: str
    category: str = "general"

class TermLibrary(BaseModel):
    id: str
    project_id: str
    name: str
    entries: List[TermEntry] = []
    created_at: str = ""

class ReaderContent(BaseModel):
    id: str
    original_text: str
    translated_text: str
    doc_type: DocumentType
    headings: List[Dict[str, Any]] = []
