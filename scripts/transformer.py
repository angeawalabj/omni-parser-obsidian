"""
Transformer Module - Surgical HTML / ENEX to Markdown Conversion
Target: Obsidian Vaults
Engine: Pandoc (GFM)
"""

from __future__ import annotations

import logging
import subprocess
import shutil
import re
import base64
import hashlib
import requests
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass

from bs4 import BeautifulSoup


# ==========================
# Result Object
# ==========================

@dataclass
class TransformResult:
    success: bool
    images_extracted: int = 0
    external_images: int = 0
    warnings: List[str] = None
    error: Optional[str] = None


# ==========================
# Transformer
# ==========================

class ContentTransformer:
    """
    High-fidelity HTML / ENEX → Markdown transformer for Obsidian
    """

    def __init__(self, pandoc_path: Optional[str] = None, timeout: int = 30):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.timeout = timeout
        self.pandoc_path = pandoc_path or shutil.which("pandoc")

        if not self.pandoc_path:
            raise RuntimeError("Pandoc not found. Install pandoc or provide explicit path.")

        self.logger.info(f"Pandoc detected at {self.pandoc_path}")

    # ==========================
    # Public API
    # ==========================

    def transform_file(
        self,
        source_file: Path,
        output_file: Path,
        attachments_dir: Path,
        download_external_images: bool = True
    ) -> TransformResult:
        warnings: List[str] = []
        images_extracted = 0
        external_images = 0

        try:
            attachments_dir.mkdir(parents=True, exist_ok=True)
            raw_content = source_file.read_text(encoding="utf-8", errors="ignore")

            html = self._extract_html(raw_content, source_file.suffix)

            html, image_map, images_extracted, external_images = self._process_images(
                html,
                source_file.stem,
                attachments_dir,
                download_external_images,
                warnings
            )

            markdown = self._convert_with_pandoc(html)
            markdown = self._finalize_markdown(markdown, image_map)

            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(markdown, encoding="utf-8")

            return TransformResult(
                success=True,
                images_extracted=images_extracted,
                external_images=external_images,
                warnings=warnings or None
            )

        except Exception as e:
            self.logger.exception("Transformation failed")
            return TransformResult(
                success=False,
                images_extracted=images_extracted,
                external_images=external_images,
                warnings=warnings or None,
                error=str(e)
            )

    # ==========================
    # HTML / ENEX Handling
    # ==========================

    def _extract_html(self, content: str, suffix: str) -> str:
        if suffix.lower() == ".enex":
            soup = BeautifulSoup(content, "xml")
            content_tag = soup.find("content")
            if not content_tag:
                raise ValueError("Invalid ENEX: <content> not found")
            return content_tag.text
        return content

    # ==========================
    # Image Processing
    # ==========================

    def _process_images(
        self,
        html: str,
        base_name: str,
        attachments_dir: Path,
        download_external: bool,
        warnings: List[str]
    ):
        soup = BeautifulSoup(html, "lxml")
        image_map: Dict[str, str] = {}

        extracted = 0
        external = 0

        for img in soup.find_all("img"):
            src = img.get("src", "").strip()
            if not src:
                continue

            # Base64 images
            if src.startswith("data:image"):
                data = self._decode_base64(src)
                if not data:
                    warnings.append("Failed to decode base64 image")
                    continue

                ext = self._image_extension(src)
                name = self._hashed_filename(base_name, data, ext)
                (attachments_dir / name).write_bytes(data)

                image_map[src] = name
                img.replace_with(self._obsidian_img(name))
                extracted += 1

            # External images
            elif src.startswith("http") and download_external:
                try:
                    resp = requests.get(src, timeout=10)
                    resp.raise_for_status()
                    ext = self._guess_extension(resp.headers.get("Content-Type"))
                    name = self._hashed_filename(base_name, resp.content, ext)
                    (attachments_dir / name).write_bytes(resp.content)

                    image_map[src] = name
                    img.replace_with(self._obsidian_img(name))
                    external += 1
                except Exception:
                    warnings.append(f"Failed to download image: {src}")
                    external += 1

        return str(soup), image_map, extracted, external

    def _decode_base64(self, data_uri: str) -> Optional[bytes]:
        try:
            _, encoded = data_uri.split(",", 1)
            return base64.b64decode(encoded)
        except Exception:
            return None

    def _image_extension(self, data_uri: str) -> str:
        match = re.search(r"image/([\w+]+)", data_uri)
        return f".{match.group(1)}" if match else ".png"

    def _guess_extension(self, content_type: Optional[str]) -> str:
        if not content_type:
            return ".png"
        if "jpeg" in content_type:
            return ".jpg"
        if "png" in content_type:
            return ".png"
        if "gif" in content_type:
            return ".gif"
        return ".img"

    def _hashed_filename(self, base: str, data: bytes, ext: str) -> str:
        h = hashlib.md5(data).hexdigest()[:12]
        return f"{base}_{h}{ext}"

    def _obsidian_img(self, filename: str):
        return BeautifulSoup(f"![[{filename}]]", "lxml")

    # ==========================
    # Pandoc
    # ==========================

    def _convert_with_pandoc(self, html: str) -> str:
        cmd = [
            self.pandoc_path,
            "--from=html",
            "--to=gfm",
            "--wrap=none",
            "--markdown-headings=atx",
        ]

        proc = subprocess.run(
            cmd,
            input=html,
            capture_output=True,
            text=True,
            timeout=self.timeout
        )

        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip())

        return proc.stdout

    # ==========================
    # Finalization
    # ==========================

    def _finalize_markdown(self, md: str, image_map: Dict[str, str]) -> str:
        # Clean leftover HTML
        md = re.sub(r"<[^>]+>", "", md)

        # Normalize excessive blank lines
        md = re.sub(r"\n{4,}", "\n\n", md)

        return md.strip()
