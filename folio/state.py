import asyncio
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
import httpx
import markdown
from pypdf import PdfReader
import reflex as rx

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

_HTTP_CLIENT = httpx.AsyncClient(
    timeout=6.0,
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    },
    follow_redirects=True,
    limits=httpx.Limits(max_keepalive_connections=20, max_connections=40),
)

async def _fast_google_translate(text: str, target: str) -> str:
    clean = text.strip()
    if not clean:
        return ""

    url = "https://translate.googleapis.com/translate_a/single"
    params = {
        "client": "gtx",
        "sl": "auto",
        "tl": target,
        "dt": "t",
        "q": clean,
    }

    try:
        res = await _HTTP_CLIENT.get(url, params=params)
        if res.status_code == 200:
            data = res.json()
            if data and isinstance(data, list) and data[0]:
                out = "".join(part[0] for part in data[0] if part and part[0])
                if out.strip():
                    return out.strip()
    except Exception as e:
        print(f"[FastTranslate Error]: {e}")

    try:
        url_dict = f"https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=auto&tl={target}&q={urllib.parse.quote(clean)}"
        res = await _HTTP_CLIENT.get(url_dict)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list) and len(data) > 0:
                return data[0] if isinstance(data[0], str) else data[0][0]
    except Exception:
        pass

    return clean

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

def _build_docx(title: str, text: str) -> bytes:
    doc = WordDocument()
    doc.add_heading(title, level=0)
    for p in text.split("\n\n"):
        if p.strip():
            doc.add_paragraph(p.strip())
    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio.getvalue()

class ReaderState(rx.State):
    # Standard Python collections per user session
    documents: list[DocumentData] = []
    translations_cache: dict[str, str] = {}

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
    is_dark: bool = False
    show_reader_window: bool = False
    mobile_shelf_open: bool = False
    mobile_view_tab: str = "split"
    translation_loading: bool = False
    translation_status: str = ""
    editing_id: str = ""
    editor_title: str = ""
    editor_text: str = ""
    current_page: int = 0

    export_format_reader: str = "docx"
    export_format_editor: str = "docx"

    def load_library(self):
        if self.documents and not self.active_id:
            self.active_id = self.documents[0]["id"]

    @rx.var
    def active_document(self) -> DocumentData:
        default_doc: DocumentData = {
            "id": "",
            "title": "",
            "filename": "",
            "format": "",
            "paragraphs": [],
            "page_data": [],
            "page_kind": "estimated",
            "words": 0,
            "pages": 0,
            "minutes": 0,
            "detected_language": "auto",
            "detected_language_name": "Auto Detect",
            "detection_error": "",
        }
        for doc in self.documents:
            if doc.get("id") == self.active_id:
                return doc
        return default_doc

    @rx.var
    def visible_paragraphs(self) -> list[str]:
        pages = self.active_document.get("page_data", [])
        return pages[self.current_page] if 0 <= self.current_page < len(pages) else []

    @rx.var
    def page_start(self) -> int:
        pages = self.active_document.get("page_data", [])
        return sum(len(page) for page in pages[:self.current_page])

    @rx.var
    def visible_translations(self) -> list[str]:
        paras = self.visible_paragraphs
        start = self.page_start
        doc_id = self.active_document.get("id", "")
        res = []
        for idx in range(len(paras)):
            key = f"{doc_id}:{start + idx}"
            res.append(self.translations_cache.get(key, ""))
        return res

    @rx.var
    def full_translated_document_text(self) -> str:
        doc = self.active_document
        paras = doc.get("paragraphs", [])
        if not paras:
            return ""
        doc_id = doc.get("id", "")
        out = []
        for idx, p in enumerate(paras):
            key = f"{doc_id}:{idx}"
            trans = self.translations_cache.get(key)
            out.append(trans.strip() if trans and trans.strip() else f"[{p}]")
        return "\n\n".join(out)

    def toggle_theme(self):
        self.is_dark = not self.is_dark

    def toggle_reader_window(self):
        self.show_reader_window = not self.show_reader_window

    def toggle_mobile_shelf(self):
        self.mobile_shelf_open = not self.mobile_shelf_open

    def close_mobile_shelf(self):
        self.mobile_shelf_open = False

    def set_mobile_tab(self, tab: str):
        self.mobile_view_tab = tab

    def set_export_format_reader(self, fmt: str):
        self.export_format_reader = fmt

    def set_export_format_editor(self, fmt: str):
        self.export_format_editor = fmt

    def speak_text(self, text: str):
        if not text.strip():
            return
        safe_text = json.dumps(text.strip())
        target_lang = self.target_language
        lang_tag = f"{target_lang}-IN" if target_lang in ["ml", "hi", "ta", "te", "kn"] else target_lang
        script = f"""
        if ('speechSynthesis' in window) {{
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance({safe_text});
            utterance.lang = '{lang_tag}';
            utterance.rate = 0.95;
            window.speechSynthesis.speak(utterance);
        }}
        """
        return rx.call_script(script)

    def export_translation_from_reader(self):
        doc = self.active_document
        text = self.full_translated_document_text
        if not text:
            return
        title = f"{doc.get('title', 'Document')}_{self.target_language.upper()}"
        clean_name = title.replace(" ", "_")

        fmt = self.export_format_reader
        if fmt == "docx":
            file_bytes = _build_docx(title, text)
            return rx.download(data=file_bytes, filename=f"{clean_name}.docx")
        elif fmt == "md":
            md_content = f"# {title}\n\n{text}"
            return rx.download(data=md_content, filename=f"{clean_name}.md")
        elif fmt == "pdf":
            return rx.call_script("window.print();")
        else:
            return rx.download(data=text, filename=f"{clean_name}.txt")

    def export_editor_text(self):
        title = self.editor_title.strip() or "Untitled Document"
        content = self.editor_text.strip()
        clean_name = title.replace(" ", "_")

        fmt = self.export_format_editor
        if fmt == "docx":
            file_bytes = _build_docx(title, content)
            return rx.download(data=file_bytes, filename=f"{clean_name}.docx")
        elif fmt == "md":
            md_content = f"# {title}\n\n{content}"
            return rx.download(data=md_content, filename=f"{clean_name}.md")
        elif fmt == "pdf":
            return rx.call_script("window.print();")
        else:
            return rx.download(data=content, filename=f"{clean_name}.txt")

    def create_new_document(self):
        new_id = str(uuid.uuid4())
        doc: DocumentData = {
            "id": new_id,
            "title": "Untitled Document",
            "filename": "untitled.txt",
            "format": "TXT",
            "paragraphs": [""],
            "page_data": [[""]],
            "page_kind": "estimated",
            "words": 0,
            "pages": 1,
            "minutes": 1,
            "detected_language": "auto",
            "detected_language_name": "Auto Detect",
            "detection_error": "",
        }
        self.documents.append(doc)
        self.active_id = new_id
        self.current_page = 0
        self.editing_id = new_id
        self.editor_title = "Untitled Document"
        self.editor_text = ""
        self.mobile_shelf_open = False
        return rx.redirect("/edit")

    def change_page(self, direction: int):
        nxt = self.current_page + direction
        total_pages = self.active_document.get("pages", 1)
        if 0 <= nxt < total_pages:
            self.current_page = nxt
            self.selected_passage = -1

    def select_document(self, doc_id: str):
        self.active_id = doc_id
        self.current_page = 0
        self.selected_passage = -1
        self.translation_status = ""
        self.mobile_shelf_open = False

    def remove_document(self, doc_id: str):
        self.documents = [d for d in self.documents if d.get("id") != doc_id]
        if self.active_id == doc_id:
            if self.documents:
                self.select_document(self.documents[-1]["id"])
            else:
                self.active_id = ""
                self.current_page = 0

    async def handle_upload(self, files: list[rx.UploadFile]):
        if not files:
            return
        self.is_loading = True
        self.error_message = ""
        yield

        last_id = ""
        for file in files:
            name = Path(file.filename or "file").name
            suffix = Path(name).suffix.lower()
            try:
                data = await file.read()
                pages, kind = _extract(data, suffix)
                paras = [p for page in pages for p in page]
                words = len("\n\n".join(paras).split())
                doc_id = str(uuid.uuid4())
                doc: DocumentData = {
                    "id": doc_id,
                    "title": Path(name).stem.replace("_", " ").title(),
                    "filename": name,
                    "format": suffix.lstrip(".").upper(),
                    "paragraphs": paras,
                    "page_data": pages,
                    "page_kind": kind,
                    "words": words,
                    "pages": len(pages),
                    "minutes": max(1, math.ceil(words / 220)),
                    "detected_language": "auto",
                    "detected_language_name": "Auto Detect",
                    "detection_error": "",
                }
                self.documents.append(doc)
                last_id = doc_id
            except Exception as e:
                self.error_message = f"{name}: {str(e)}"
                print(f"[Upload Error]: {e}")

        if last_id:
            self.select_document(last_id)

        self.is_loading = False
        self.mobile_shelf_open = False
        yield rx.clear_selected_files("documents")

    def open_editor(self):
        doc = self.active_document
        self.editing_id = doc.get("id", "")
        self.editor_title = doc.get("title", "")
        self.editor_text = "\n\n".join(doc.get("paragraphs", []))
        return rx.redirect("/edit")

    def set_editor_title(self, val: str):
        self.editor_title = val

    def set_editor_text(self, val: str):
        self.editor_text = val

    def save_edit(self, form_data: dict[str, Any]):
        title = form_data.get("title", "").strip() or self.editor_title.strip() or "Untitled Document"
        text = _normalize(form_data.get("text", "") or self.editor_text)
        pages = _paginate(text) if text else [[""]]
        paras = [p for page in pages for p in page]
        words = len(text.split())

        for i, doc in enumerate(self.documents):
            if doc.get("id") == self.editing_id:
                self.documents[i].update({
                    "title": title,
                    "paragraphs": paras,
                    "page_data": pages,
                    "words": words,
                    "pages": len(pages),
                    "minutes": max(1, math.ceil(words / 220)),
                })
                break
        return rx.redirect("/")

    def select_passage(self, index: int):
        self.selected_passage = index
        self.translation_status = f"Selected Passage {index + 1}."

    def set_target_language(self, code: str):
        self.target_language = code

    async def translate_selected_passage(self):
        paras = self.active_document.get("paragraphs", [])
        if self.selected_passage < 0 or self.selected_passage >= len(paras):
            self.translation_status = "⚠️ Click a passage on the left to select it."
            return

        self.translation_loading = True
        self.translation_status = f"Translating Passage {self.selected_passage + 1}..."
        yield

        target = self.target_language
        text = paras[self.selected_passage]
        translated = await _fast_google_translate(text, target)

        self.translations_cache[f"{self.active_id}:{self.selected_passage}"] = translated
        self.translation_loading = False
        self.translation_status = "✅ Done."

    async def translate_entire_page(self):
        paras = self.active_document.get("paragraphs", [])
        if not paras:
            return

        self.translation_loading = True
        self.translation_status = "Translating current page..."
        yield

        target = self.target_language
        start_idx = self.page_start
        end_idx = min(len(paras), start_idx + len(self.visible_paragraphs))

        page_paras = [paras[i] for i in range(start_idx, end_idx)]
        indices = list(range(start_idx, end_idx))

        delimiter = "\n\n§§§\n\n"
        combined = delimiter.join(page_paras)

        result = await _fast_google_translate(combined, target)
        parts = [p.strip() for p in result.split("§§§")]

        if len(parts) == len(page_paras):
            for idx, text in zip(indices, parts):
                self.translations_cache[f"{self.active_id}:{idx}"] = text
        else:
            tasks = [_fast_google_translate(p, target) for p in page_paras]
            results = await asyncio.gather(*tasks)
            for idx, text in zip(indices, results):
                self.translations_cache[f"{self.active_id}:{idx}"] = text

        self.translation_loading = False
        self.translation_status = "✅ Page translated."

    def decrease_font(self): self.font_size = max(14, self.font_size - 1)
    def increase_font(self): self.font_size = min(28, self.font_size + 1)
    def toggle_width(self):
        self.reading_width = "Wide" if self.reading_width == "Comfortable" else "Comfortable"
    def cycle_spacing(self):
        self.line_spacing = {"Compact": "Relaxed", "Relaxed": "Airy", "Airy": "Compact"}[self.line_spacing]