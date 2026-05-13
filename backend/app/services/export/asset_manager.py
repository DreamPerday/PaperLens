import os
import re
import base64
import hashlib
from io import BytesIO
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from PIL import Image

class AssetManager:
    def __init__(self, base_path: str = "storage"):
        self.base_path = Path(base_path)
        self.cache: Dict[str, str] = {}
        self.processed_images: set = set()
        
    async def collect_images(self, content: str, doc_id: str) -> Tuple[str, List[dict]]:
        img_pattern = r'<img[^>]+src="([^"]+)"[^>]*\/?>'
        matches = list(re.finditer(img_pattern, content))
        images = []
        
        for match in matches:
            src = match.group(1)
            if src in self.processed_images:
                continue
            
            if src.startswith("data:image/"):
                images.append({"src": src, "type": "base64", "original": src})
                self.processed_images.add(src)
                continue
            
            if src.startswith("/"):
                full_path = self.base_path / src.lstrip("/")
            elif src.startswith("http"):
                images.append({"src": src, "type": "remote", "original": src})
                self.processed_images.add(src)
                continue
            else:
                full_path = self.base_path / src
            
            if full_path.exists():
                images.append({"src": str(full_path), "type": "local", "original": src})
                self.processed_images.add(src)
        
        return content, images
    
    def image_to_base64(self, image_path: str, quality: int = 85) -> str:
        if image_path in self.cache:
            return self.cache[image_path]
        
        try:
            with Image.open(image_path) as img:
                img = img.convert("RGB")
                buffer = BytesIO()
                img.save(buffer, format="JPEG", quality=quality)
                base64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
                result = f"data:image/jpeg;base64,{base64_str}"
                self.cache[image_path] = result
                return result
        except Exception as e:
            print(f"Failed to convert {image_path}: {e}")
            return f"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    
    async def embed_images(self, content: str, doc_id: str, embed_type: str = "base64") -> str:
        _, images = await self.collect_images(content, doc_id)
        
        for img in images:
            if img["type"] == "local":
                if embed_type == "base64":
                    base64_data = self.image_to_base64(img["src"])
                    content = content.replace(img["original"], base64_data)
                else:
                    rel_path = f"/assets/{os.path.basename(img['src'])}"
                    content = content.replace(img["original"], rel_path)
        
        return content
    
    def clear_cache(self):
        self.cache.clear()
        self.processed_images.clear()
    
    def clear_processed_only(self):
        self.processed_images.clear()
    
    def get_cache_size(self) -> int:
        return len(self.cache)
    
    @staticmethod
    def generate_hash(content: bytes) -> str:
        return hashlib.md5(content).hexdigest()
