from app.config import settings
import json
import os
from typing import Optional, Dict, List
from datetime import datetime
import uuid
from pathlib import Path

class StorageService:
    def __init__(self):
        self.base = Path(settings.storage_path)
        self.projects_file = self.base / "projects.json"
        self._ensure_storage()

    def _ensure_storage(self):
        (self.base / "projects").mkdir(parents=True, exist_ok=True)
        (self.base / "uploads").mkdir(parents=True, exist_ok=True)
        (self.base / "translations").mkdir(parents=True, exist_ok=True)
        if not self.projects_file.exists():
            self.projects_file.write_text("[]", encoding="utf-8")

    def _read_json(self, path: Path) -> list:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return []

    def _write_json(self, path: Path, data: list):
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # --- Projects ---
    def list_projects(self) -> list:
        return self._read_json(self.projects_file)

    def get_project(self, project_id: str) -> Optional[dict]:
        projects = self.list_projects()
        for p in projects:
            if p["id"] == project_id:
                return p
        return None

    def create_project(self, name: str, description: str = "") -> dict:
        projects = self.list_projects()
        now = datetime.now().isoformat()
        project = {
            "id": str(uuid.uuid4()),
            "name": name,
            "description": description,
            "status": "active",
            "created_at": now,
            "updated_at": now,
            "file_count": 0,
            "total_tokens": 0,
        }
        projects.append(project)
        self._write_json(self.projects_file, projects)
        (self.base / "projects" / project["id"]).mkdir(exist_ok=True)
        return project

    def update_project(self, project_id: str, data: dict) -> Optional[dict]:
        projects = self.list_projects()
        for i, p in enumerate(projects):
            if p["id"] == project_id:
                projects[i].update(data)
                projects[i]["updated_at"] = datetime.now().isoformat()
                self._write_json(self.projects_file, projects)
                return projects[i]
        return None

    def delete_project(self, project_id: str) -> bool:
        projects = self.list_projects()
        filtered = [p for p in projects if p["id"] != project_id]
        if len(filtered) != len(projects):
            self._write_json(self.projects_file, filtered)
            import shutil
            shutil.rmtree(str(self.base / "projects" / project_id), ignore_errors=True)
            return True
        return False

    # --- Documents ---
    def _get_docs_file(self, project_id: str) -> Path:
        return self.base / "projects" / project_id / "documents.json"

    def list_documents(self, project_id: str) -> list:
        docs_file = self._get_docs_file(project_id)
        return self._read_json(docs_file)

    def get_document(self, project_id: str, doc_id: str) -> Optional[dict]:
        docs = self.list_documents(project_id)
        for d in docs:
            if d["id"] == doc_id:
                return d
        return None

    def add_document(self, project_id: str, filename: str, original_name: str,
                     doc_type: str, size: int, file_path: str) -> dict:
        docs_file = self._get_docs_file(project_id)
        docs = self._read_json(docs_file)
        now = datetime.now().isoformat()
        doc = {
            "id": str(uuid.uuid4()),
            "project_id": project_id,
            "filename": filename,
            "original_name": original_name,
            "doc_type": doc_type,
            "size": size,
            "status": "uploaded",
            "page_count": 0,
            "file_path": file_path,
            "created_at": now,
            "updated_at": now,
        }
        docs.append(doc)
        self._write_json(docs_file, docs)
        self.update_project(project_id, {"file_count": len(docs)})
        return doc

    def update_document(self, project_id: str, doc_id: str, data: dict) -> Optional[dict]:
        docs_file = self._get_docs_file(project_id)
        docs = self._read_json(docs_file)
        for i, d in enumerate(docs):
            if d["id"] == doc_id:
                docs[i].update(data)
                docs[i]["updated_at"] = datetime.now().isoformat()
                self._write_json(docs_file, docs)
                return docs[i]
        return None

    def delete_document(self, project_id: str, doc_id: str) -> bool:
        docs_file = self._get_docs_file(project_id)
        docs = self._read_json(docs_file)
        filtered = [d for d in docs if d["id"] != doc_id]
        if len(filtered) != len(docs):
            self._write_json(docs_file, filtered)
            self.update_project(project_id, {"file_count": len(filtered)})
            doc = self.get_document(project_id, doc_id)
            if doc and os.path.exists(doc.get("file_path", "")):
                os.remove(doc["file_path"])
            return True
        return False

    # --- Translations ---
    def _get_trans_file(self, project_id: str) -> Path:
        return self.base / "projects" / project_id / "translations.json"

    def list_translations(self, project_id: str) -> list:
        trans_file = self._get_trans_file(project_id)
        return self._read_json(trans_file)

    def get_translation(self, project_id: str, doc_id: str) -> Optional[dict]:
        translations = self.list_translations(project_id)
        for t in translations:
            if t["document_id"] == doc_id:
                return t
        return None

    def save_translation(self, project_id: str, document_id: str,
                         content: str, tokens_used: int = 0,
                         prompt_tokens: int = 0, completion_tokens: int = 0,
                         cached_tokens: int = 0) -> dict:
        trans_file = self._get_trans_file(project_id)
        translations = self._read_json(trans_file)
        now = datetime.now().isoformat()

        translation = {
            "id": str(uuid.uuid4()),
            "document_id": document_id,
            "project_id": project_id,
            "status": "completed",
            "progress": 1.0,
            "content": content,
            "tokens_used": tokens_used,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cached_tokens": cached_tokens,
            "created_at": now,
            "completed_at": now,
        }
        existing = None
        for i, t in enumerate(translations):
            if t["document_id"] == document_id:
                existing = i
                break
        if existing is not None:
            translations[existing] = translation
        else:
            translations.append(translation)
        self._write_json(trans_file, translations)

        project = self.get_project(project_id)
        if project:
            all_translations = self.list_translations(project_id)
            total_tok = sum(t.get("tokens_used", 0) for t in all_translations)
            total_prompt = sum(t.get("prompt_tokens", 0) for t in all_translations)
            total_comp = sum(t.get("completion_tokens", 0) for t in all_translations)
            total_cached = sum(t.get("cached_tokens", 0) for t in all_translations)
            self.update_project(project_id, {
                "total_tokens": total_tok,
                "total_prompt_tokens": total_prompt,
                "total_completion_tokens": total_comp,
                "total_cached_tokens": total_cached,
            })
        return translation

storage_service = StorageService()
