import asyncio
import codecs
import html
import io
import json
import math
from pathlib import Path
import re
from typing import Any, TypedDict
import urllib.parse
import uuid

from bs4 import BeautifulSoup
from docx import Document as WordDocument
from ebooklib import ITEM_DOCUMENT, epub
from langdetect import DetectorFactory, detect_langs
import markdown
from pypdf import PdfReader
import reflex as rx
import requests

DetectorFactory.seed = 0

STORAGE_DIR = Path("saved_library")
DATA_FILE = STORAGE_DIR / "library.json"

LANGUAGES = [
    {"code": "ml", "name": "Malayalam"},
    {"code": "en", "name": "English"},
    {"code": "hi", "name": "Hindi"},
    {"code": "ta", "name": "Tamil"},
    {"code": "te", "name": "Telugu"},
    {"code": "kn", "name": "Kannada"},
    {"code": "ar", "name": "Arabic"},
    {"code": "es", "name": "Spanish"},
    {"code": "fr", "name": "French"},
    {"code": "de", "name": "German"},
    {"code": "it", "name": "Italian"},
    {"code": "pt", "name": "Portuguese"},
    {"code": "ru", "name": "Russian"},
    {"code": "zh-CN", "name": "Chinese"},
    {"code": "ja", "name": "Japanese"},
]

class DocumentData(TypedDict):
    id: str
    title: str
    filename: str
    format: str
    paragraphs: list[str]
    page_data: list[list[str]]
    page_kind: str
    words: int
    pages: int
    minutes: int
    detected_language: str
    detected_language_name: str
    detection_error: str

def _detect_language(text: str) -> tuple[str, str, str]:
    sample = text.strip()[:2000]
    if len("".join(sample.split())) < 8:
        return ("auto", "Auto Detect", "")
    try:
        guesses = detect_langs(sample)
        if guesses and guesses[0].prob >= 0.70:
            detected = guesses[0].lang.lower()
            match = next((item for item in LANGUAGES if item["code"].lower() == detected), None)
            if match:
                return match["code"], match["name"], ""
    except Exception:
        pass
    return ("auto", "Auto Detect", "")

def _translate_single_text(text: str, source: str, target: str) -> str:
    if not text.strip():
        return ""

    src = "auto" if not source or source == "auto" else source

    # 1. Google Translate Mobile Client
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": src,
            "tl": target,
            "dt": "t",
            "q": text.strip()
        }
        headers = {
            "User-Agent": "AndroidTranslate/5.3.0.RC02.130475354-53000263 5.1 phone TRANSLATE_OPM5_TEST_1"
        }
        res = requests.get(url, params=params, headers=headers, timeout=12)
        if res.status_code == 200:
            data = res.json()
            if data and isinstance(data, list) and data[0]:
                translated = "".join(part[0] for part in data[0] if part and part[0])
                if translated.strip():
                    return translated.strip()
    except Exception as e:
        print(f"[Folio Translation] Primary engine error: {e}")

    # 2. Lingva Translate Mirror
    try:
        url = f"https://lingva.ml/api/v1/{src}/{target}/{urllib.parse.quote(text.strip())}"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if "translation" in data and data["translation"].strip():
                return data["translation"].strip()
    except Exception as e:
        print(f"[Folio Translation] Lingva mirror error: {e}")

    # 3. MyMemory fallback
    try:
        pair = f"{'en' if src == 'auto' else src}|{target}"
        url = f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(text.strip()[:450])}&langpair={pair}"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if data.get("responseStatus") == 200:
                return html.unescape(data["responseData"]["translatedText"]).strip()
    except Exception as e:
        print(f"[Folio Translation] MyMemory error: {e}")

    return f"[Translation temporarily rate-limited. Please wait a few seconds.]"

def _normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    text = re.sub(r"[\t\u00a0 ]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()

def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")

def _html_to_text(source: str) -> str:
    soup = BeautifulSoup(source, "html.parser")
    for el in soup(["script", "style", "noscript", "svg", "nav", "footer", "header", "form"]):
        el.decompose()
    for el in soup.find_all(["p", "div", "section", "article", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote", "br"]):
        el.insert_before("\n\n")
    return _normalize(soup.get_text(separator=""))

def _paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

def _paginate(text: str) -> list[list[str]]:
    pages, current, count = [], [], 0
    for para in _paragraphs(text):
        words = para.split()
        while words:
            space = 250 - count
            if count and (len(words) > space or (count >= 180 and len(words) > 70)):
                pages.append(current)
                current, count, space = [], 0, 250
            take = min(len(words), space)
            current.append(" ".join(words[:take]))
            words = words[take:]
            count += take
            if words:
                pages.append(current)
                current, count = [], 0
    if current:
        pages.append(current)
    return pages

def _extract(data: bytes, suffix: str) -> tuple[list[list[str]], str]:
    if suffix == ".pdf":
        reader = PdfReader(io.BytesIO(data))
        pages = [_paragraphs(_normalize(p.extract_text() or "")) for p in reader.pages]
        if not any(pages):
            raise ValueError("No readable text found in PDF.")
        return pages, "pdf"
    elif suffix == ".docx":
        doc = WordDocument(io.BytesIO(data))
        text = _normalize("\n\n".join(p.text for p in doc.paragraphs if p.text))
    elif suffix == ".epub":
        book = epub.read_epub(io.BytesIO(data))
        parts = [_html_to_text(item.get_content().decode("utf-8", errors="replace"))
                 for item in book.get_items_of_type(ITEM_DOCUMENT)]
        text = _normalize("\n\n".join(parts))
    elif suffix in (".html", ".htm"):
        text = _html_to_text(_decode_text(data))
    elif suffix in (".md", ".markdown"):
        text = _html_to_text(markdown.markdown(_decode_text(data)))
    else:
        text = _normalize(_decode_text(data))
    if not text:
        raise ValueError("File contains no readable text.")
    return _paginate(text), "estimated"

class ReaderState(rx.State):
    documents: list[DocumentData] = []
    active_id: str = ""
    error_message: str = ""
    is_loading: bool = False
    progress: int = 0
    font_size: int = 18
    line_spacing: str = "Relaxed"
    reading_width: str = "Comfortable"
    languages: list[dict[str, str]] = LANGUAGES
    target_language: str = "ml"
    selected_passage: int = -1
    translations_cache: dict[str, str] = {}
    translation_loading: bool = False
    translation_status: str = ""
    editing_id: str = ""
    editor_title: str = ""
    editor_text: str = ""
    current_page: int = 0

    def _persist(self):
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.documents, f, ensure_ascii=False, indent=2)

    def load_library(self):
        if DATA_FILE.exists():
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    self.documents = json.load(f)
                    if self.documents and not self.active_id:
                        self.select_document(self.documents[0]["id"])
            except Exception:
                self.documents = []

    @rx.var
    def active_document(self) -> DocumentData:
        return next(
            (doc for doc in self.documents if doc["id"] == self.active_id),
            {"id": "", "title": "", "filename": "", "format": "", "paragraphs": [], "page_data": [],
             "page_kind": "estimated", "words": 0, "pages": 0, "minutes": 0, "detected_language": "",
             "detected_language_name": "Not detected", "detection_error": ""}
        )

    @rx.var
    def visible_paragraphs(self) -> list[str]:
        pages = self.active_document["page_data"]
        return pages[self.current_page] if 0 <= self.current_page < len(pages) else []

    @rx.var
    def page_start(self) -> int:
        return sum(len(page) for page in self.active_document["page_data"][:self.current_page])

    @rx.var
    def visible_translations(self) -> list[str]:
        paras = self.visible_paragraphs
        start = self.page_start
        doc_id = self.active_id
        res = []
        for idx in range(len(paras)):
            key = f"{doc_id}:{start + idx}"
            res.append(self.translations_cache.get(key, ""))
        return res

    def change_page(self, direction: int):
        nxt = self.current_page + direction
        if 0 <= nxt < self.active_document["pages"]:
            self.current_page = nxt
            self.selected_passage = -1

    def select_document(self, doc_id: str):
        self.active_id = doc_id
        self.current_page = 0
        self.selected_passage = -1
        self.translation_status = ""

    def remove_document(self, doc_id: str):
        self.documents = [d for d in self.documents if d["id"] != doc_id]
        if self.active_id == doc_id:
            if self.documents:
                self.select_document(self.documents[-1]["id"])
            else:
                self.active_id = ""
                self.current_page = 0
        self._persist()

    def update_progress(self, progress: dict):
        self.progress = round(progress.get("progress", 0.0) * 100)

    async def handle_upload(self, files: list[rx.UploadFile]):
        if not files:
            return
        self.is_loading = True
        yield
        for file in files:
            name = Path(file.filename or "file").name
            suffix = Path(name).suffix.lower()
            try:
                data = await file.read()
                pages, kind = _extract(data, suffix)
                paras = [p for page in pages for p in page]
                txt = "\n\n".join(paras)
                code, lang_name, err = _detect_language(txt)
                words = len(txt.split())
                doc: DocumentData = {
                    "id": str(uuid.uuid4()),
                    "title": Path(name).stem.replace("_", " ").title(),
                    "filename": name,
                    "format": suffix.lstrip(".").upper(),
                    "paragraphs": paras,
                    "page_data": pages,
                    "page_kind": kind,
                    "words": words,
                    "pages": len(pages),
                    "minutes": max(1, math.ceil(words / 220)),
                    "detected_language": code,
                    "detected_language_name": lang_name,
                    "detection_error": err,
                }
                self.documents.append(doc)
                self.select_document(doc["id"])
            except Exception as e:
                self.error_message = f"{name}: {str(e)}"
        self._persist()
        self.is_loading = False
        yield rx.clear_selected_files("documents")

    def open_editor(self):
        doc = self.active_document
        self.editing_id = doc["id"]
        self.editor_title = doc["title"]
        self.editor_text = "\n\n".join(doc["paragraphs"])
        return rx.redirect("/edit")

    def save_edit(self, form_data: dict[str, Any]):
        title = form_data.get("title", "").strip()
        text = _normalize(form_data.get("text", ""))
        pages = _paginate(text)
        paras = [p for page in pages for p in page]
        words = len(text.split())
        code, lang_name, err = _detect_language(text)

        for i, doc in enumerate(self.documents):
            if doc["id"] == self.editing_id:
                self.documents[i].update({
                    "title": title,
                    "paragraphs": paras,
                    "page_data": pages,
                    "words": words,
                    "pages": len(pages),
                    "minutes": max(1, math.ceil(words / 220)),
                    "detected_language": code,
                    "detected_language_name": lang_name,
                    "detection_error": err,
                })
                break
        self._persist()
        return rx.redirect("/")

    def select_passage(self, index: int):
        self.selected_passage = index
        self.translation_status = f"Selected Passage {index + 1}."

    def set_target_language(self, code: str):
        self.target_language = code

    async def translate_selected_passage(self):
        paras = self.active_document["paragraphs"]
        if self.selected_passage < 0 or self.selected_passage >= len(paras):
            self.translation_status = "⚠️ Please click on a paragraph on the left first."
            return

        self.translation_loading = True
        self.translation_status = f"Translating Passage {self.selected_passage + 1} to {self.target_language}..."
        yield

        source = self.active_document["detected_language"] or "auto"
        target = self.target_language
        text = paras[self.selected_passage]

        print(f"[Folio] Translating passage {self.selected_passage + 1} into {target}...")
        res = await asyncio.to_thread(_translate_single_text, text, source, target)

        key = f"{self.active_id}:{self.selected_passage}"
        new_cache = dict(self.translations_cache)
        new_cache[key] = res
        self.translations_cache = new_cache

        self.translation_loading = False
        self.translation_status = "✅ Passage translated."

    async def translate_entire_page(self):
        paras = self.active_document["paragraphs"]
        if not paras:
            return

        self.translation_loading = True
        self.translation_status = f"Translating page to {self.target_language} in one batch..."
        yield

        source = self.active_document["detected_language"] or "auto"
        target = self.target_language
        start_idx = self.page_start
        end_idx = min(len(paras), start_idx + len(self.visible_paragraphs))

        page_paras = paras[start_idx:end_idx]
        if not page_paras:
            self.translation_loading = False
            return

        delimiter = "\n---FL_SEP---\n"
        combined_text = delimiter.join(page_paras)

        print(f"[Folio] Batch translating page ({len(page_paras)} passages) into {target}...")
        combined_translation = await asyncio.to_thread(_translate_single_text, combined_text, source, target)

        translated_parts = combined_translation.split("---FL_SEP---")

        new_cache = dict(self.translations_cache)
        for offset, part in enumerate(translated_parts):
            target_idx = start_idx + offset
            if target_idx < end_idx:
                new_cache[f"{self.active_id}:{target_idx}"] = part.strip()

        if len(translated_parts) != len(page_paras):
            for i in range(start_idx, end_idx):
                res = await asyncio.to_thread(_translate_single_text, paras[i], source, target)
                new_cache[f"{self.active_id}:{i}"] = res
                self.translations_cache = dict(new_cache)
                yield
                await asyncio.sleep(0.6)

        self.translations_cache = dict(new_cache)
        self.translation_loading = False
        self.translation_status = "✅ Page translation complete."

    def decrease_font(self): self.font_size = max(14, self.font_size - 1)
    def increase_font(self): self.font_size = min(26, self.font_size + 1)
    def toggle_width(self):
        self.reading_width = "Wide" if self.reading_width == "Comfortable" else "Comfortable"
    def cycle_spacing(self):
        self.line_spacing = {"Compact": "Relaxed", "Relaxed": "Airy", "Airy": "Compact"}[self.line_spacing]