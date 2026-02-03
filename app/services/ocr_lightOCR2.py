import requests
import base64
import os
import json
import time
import re

try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    print("⚠️ python-docx not installed - DOCX support disabled")


class GemmaOCRService:
    
    def __init__(self, api_url="http://127.0.0.1:1234/v1/chat/completions"):
        self.api_url = api_url
        self.model = "google/gemma-3-12b"
        self.timeout = 600
        self.fields = []  # Pola pobrane z szablonu HTML
        
        print(f"🔗 OCR API: {self.api_url}")
        self._check_connection()
    
    def _check_connection(self):
        try:
            response = requests.get("http://127.0.0.1:1234/v1/models", timeout=5)
            if response.status_code == 200:
                print("✅ Połączono z LM Studio!")
        except:
            print("⚠️ LM Studio nie odpowiada")
    
    def load_model(self):
        pass
    
    def unload_model(self):
        print("✅ Zakończono przetwarzanie")
    
    def set_template(self, template_path):
        """Pobiera pola z szablonu HTML (atrybuty name z inputów)."""
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.fields = list(set(re.findall(r'name=["\']([^"\']+)["\']', content)))
            print(f"📋 Pobrano {len(self.fields)} pól z szablonu")
        except Exception as e:
            print(f"⚠️ Błąd odczytu szablonu: {e}")
            self.fields = []
    
    def _image_to_base64(self, path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    
    def _get_mime_type(self, path):
        ext = os.path.splitext(path)[1].lower()
        return {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(ext, "image/png")
    
    def _extract_text_from_docx(self, path):
        """Wyciąga tekst z pliku DOCX."""
        if not DOCX_AVAILABLE:
            raise Exception("python-docx nie jest zainstalowane")
        doc = DocxDocument(path)
        return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    
    def predict(self, file_path):
        """Wysyła plik do API i zwraca wynik."""
        print(f"📤 Przetwarzanie: {os.path.basename(file_path)}")
        
        ext = os.path.splitext(file_path)[1].lower()
        
        # Dla plików DOCX - wyciągnij tekst
        if ext in ['.docx', '.doc']:
            print("📄 Wykryto dokument Word - ekstrakcja tekstu...")
            text_content = self._extract_text_from_docx(file_path)
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "Jesteś asystentem. Wyodrębniasz dane z dokumentów i zwracasz je jako JSON."},
                    {
                        "role": "user",
                        "content": f"Przeanalizuj poniższy tekst dokumentu i wyodrębnij dane.\n\n--- TEKST DOKUMENTU ---\n{text_content}\n--- KONIEC ---\n\n{self._build_prompt(is_text=True)}"
                    }
                ],
                "max_tokens": 2048,
                "temperature": 0.1
            }
        else:
            # Dla obrazów - wyślij jako base64
            image_base64 = self._image_to_base64(file_path)
            mime_type = self._get_mime_type(file_path)
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "Jesteś asystentem OCR. Wyodrębniasz dane z dokumentów i zwracasz je jako JSON."},
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_base64}"}},
                            {"type": "text", "text": self._build_prompt(is_text=False)}
                        ]
                    }
                ],
                "max_tokens": 2048,
                "temperature": 0.1
            }
        
        print(f"⏳ Oczekiwanie na odpowiedź...")
        
        response = requests.post(self.api_url, json=payload, headers={"Content-Type": "application/json"}, timeout=self.timeout)
        
        if response.status_code == 200:
            result = response.json()
            output_text = result["choices"][0]["message"]["content"]
            print("✅ Przetwarzanie zakończone!")
            return [OCRResult(output_text, file_path)]
        else:
            raise Exception(f"API błąd {response.status_code}: {response.text}")
    
    def _build_prompt(self, is_text=False):
        """Buduje prompt z pól szablonu HTML lub używa domyślnych."""
        if self.fields:
            fields_list = "\n".join([f'{i+1}. "{f}": {f.replace("_", " ")}' for i, f in enumerate(self.fields)])
        else:
            fields_list = """1. "sprzedawca_nazwa": Nazwa firmy sprzedawcy
2. "sprzedawca_adres": Adres sprzedawcy  
3. "sprzedawca_nip": NIP sprzedawcy
4. "numer_faktury": Numer faktury
5. "nabywca_nazwa": Nazwa nabywcy
6. "nabywca_adres": Adres nabywcy
7. "nabywca_nip": NIP nabywcy
8. "data_wystawienia": Data wystawienia (RRRR-MM-DD)
9. "kwota_brutto": Kwota do zapłaty
10. "termin_platnosci": Termin płatności
11. "numer_konta": Numer konta bankowego"""
        
        action = "Przeanalizuj tekst" if is_text else "Przeanalizuj obraz"
        return f"""{action} i wyodrębnij dane. Zwróć TYLKO obiekt JSON (bez markdown).

Pola do ekstrakcji:
{fields_list}

Jeśli wartości nie ma, użyj null."""


class OCRResult:
    
    def __init__(self, text, input_path):
        self.text = text
        self.input_path = input_path
        self.extracted_data = self._parse_json(text)
        self.parsing_res_list = [{"block_content": text}]
    
    def _parse_json(self, text):
        try:
            clean = text.strip()
            if clean.startswith("```"):
                lines = clean.split("\n")
                clean = "\n".join(lines[1:-1])
            return json.loads(clean)
        except:
            return {}
    
    def save_to_json(self, save_path):
        filename = os.path.basename(self.input_path)
        base_name = os.path.splitext(filename)[0]
        output_filename = f"{base_name}_{int(time.time())}.json"
        full_path = os.path.join(save_path, output_filename)
        
        data = {
            "input_path": self.input_path,
            "parsing_res_list": self.parsing_res_list,
            "full_text": self.text,
            "extracted_fields": self.extracted_data
        }
        
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"💾 Zapisano: {output_filename}")
            return full_path
        except Exception as e:
            print(f"⚠️ Błąd zapisu: {e}")
            return None
