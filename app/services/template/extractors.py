import io
import os
import tempfile

from app.services.template.exceptions import UnsupportedTemplateFileError, UnprocessableTemplateFileError

def _looks_like_binary_text(text: str) -> bool:
    if '\x00' in text:
        return True
    if not text:
        return False
    import unicodedata
    disallowed_controls = sum(
        1
        for char in text
        if unicodedata.category(char) == 'Cc' and char not in {'\n', '\r', '\t'}
    )
    return disallowed_controls > 0

def _extract_text_from_txt(content: bytes) -> str:
    """Decode a UTF-8 .txt file and return its text."""
    try:
        text = content.decode('utf-8-sig', errors='strict')
    except UnicodeDecodeError as exc:
        raise UnsupportedTemplateFileError(
            'Plik musi byc tekstem zakodowanym w UTF-8'
        ) from exc
    if _looks_like_binary_text(text):
        raise UnsupportedTemplateFileError('Plik zawiera dane binarne')
    return text


def _extract_text_from_pdf(content: bytes) -> str:
    """Extract text from a PDF using PyMuPDF (fitz)."""
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise UnsupportedTemplateFileError(
            'Brak biblioteki PyMuPDF do obslugi plikow PDF'
        ) from exc
    try:
        doc = fitz.open(stream=content, filetype='pdf')
        pages = []
        for page in doc:
            pages.append(page.get_text())
        doc.close()
        return '\n'.join(pages)
    except Exception as exc:
        raise UnprocessableTemplateFileError(
            'Nie udalo sie odczytac pliku PDF'
        ) from exc


def _extract_text_from_docx(content: bytes) -> str:
    """Extract text from a .docx file using python-docx."""
    try:
        from docx import Document
    except ImportError as exc:
        raise UnsupportedTemplateFileError(
            'Brak biblioteki python-docx do obslugi plikow DOCX'
        ) from exc
    try:
        doc = Document(io.BytesIO(content))
        paragraphs = [p.text for p in doc.paragraphs]
        return '\n'.join(paragraphs)
    except Exception as exc:
        raise UnprocessableTemplateFileError(
            'Nie udalo sie odczytac pliku DOCX'
        ) from exc


def _extract_text_from_doc(content: bytes) -> str:
    """Extract text from a legacy .doc file.

    Uses pywin32 COM automation on Windows. Falls back to a raw binary text
    extraction heuristic on non-Windows platforms.
    """
    if os.name == 'nt':
        try:
            import pythoncom
            import win32com.client
        except ImportError as exc:
            raise UnsupportedTemplateFileError(
                'Brak biblioteki pywin32 do obslugi plikow DOC'
            ) from exc
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                suffix='.doc', delete=False,
            ) as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            pythoncom.CoInitialize()
            try:
                word = win32com.client.Dispatch('Word.Application')
                word.Visible = False
                doc = word.Documents.Open(tmp_path, ReadOnly=True)
                text = doc.Content.Text
                doc.Close(False)
                word.Quit()
            finally:
                pythoncom.CoUninitialize()
            return text
        except Exception as exc:
            raise UnprocessableTemplateFileError(
                'Nie udalo sie odczytac pliku DOC'
            ) from exc
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
    else:
        # Fallback: attempt raw text extraction from binary .doc
        try:
            text_chunks = []
            i = 0
            while i < len(content):
                if content[i:i+1] == b'\x00':
                    i += 1
                    continue
                if 0x20 <= content[i] <= 0x7e or content[i] in (0x0a, 0x0d, 0x09):
                    text_chunks.append(chr(content[i]))
                i += 1
            text = ''.join(text_chunks)
            # Filter out junk — keep only runs of 4+ printable chars
            import re as _re
            runs = _re.findall(r'[\x20-\x7e\n\r\t]{4,}', text)
            return '\n'.join(runs)
        except Exception as exc:
            raise UnprocessableTemplateFileError(
                'Nie udalo sie odczytac pliku DOC'
            ) from exc


def _extract_text_from_rtf(content: bytes) -> str:
    """Extract text from an RTF file using striprtf."""
    try:
        from striprtf.striprtf import rtf_to_text
    except ImportError as exc:
        raise UnsupportedTemplateFileError(
            'Brak biblioteki striprtf do obslugi plikow RTF'
        ) from exc
    try:
        rtf_content = content.decode('utf-8', errors='replace')
        return rtf_to_text(rtf_content)
    except Exception as exc:
        raise UnprocessableTemplateFileError(
            'Nie udalo sie odczytac pliku RTF'
        ) from exc


def _extract_text_from_odt(content: bytes) -> str:
    """Extract text from an ODT file using odfpy."""
    try:
        from odf.opendocument import load as odf_load
        from odf.text import P as OdfParagraph
        from odf import teletype
    except ImportError as exc:
        raise UnsupportedTemplateFileError(
            'Brak biblioteki odfpy do obslugi plikow ODT'
        ) from exc
    try:
        doc = odf_load(io.BytesIO(content))
        paragraphs = doc.getElementsByType(OdfParagraph)
        return '\n'.join(teletype.extractText(p) for p in paragraphs)
    except Exception as exc:
        raise UnprocessableTemplateFileError(
            'Nie udalo sie odczytac pliku ODT'
        ) from exc


_TEXT_EXTRACTORS: Dict[str, Callable[[bytes], str]] = {
    '.txt': _extract_text_from_txt,
    '.pdf': _extract_text_from_pdf,
    '.docx': _extract_text_from_docx,
    '.doc': _extract_text_from_doc,
    '.rtf': _extract_text_from_rtf,
    '.odt': _extract_text_from_odt,
}