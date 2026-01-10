# 📄 Smart Document Generator

![Status](https://img.shields.io/badge/Status-Development-indigo?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.8+-yellow?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Web%20Framework-lightgrey?style=for-the-badge&logo=flask&logoColor=white)
![Tailwind](https://img.shields.io/badge/Tailwind_CSS-Dark_Mode-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)

**Smart Document Generator** to aplikacja webowa automatyzująca proces przenoszenia danych z systemów OCR do profesjonalnych szablonów HTML/PDF.

---

## 💡 Główne Funkcje

* **🔍 Inteligentny OCR Matching**
    Algorytm automatycznie wyszukuje słowa kluczowe (np. `"NIP"`, `"Konto"`) w nieustrukturyzowanych blokach tekstu i przypisuje je do pól formularza.
* **👁️ Live Preview**
    Podgląd dokumentu w czasie rzeczywistym podczas edycji danych.
* **📄 Generowanie PDF**
    Eksport gotowych umów i faktur z zachowaniem stylów CSS.
* **🌙 Dark Mode UI**
    Nowoczesny interfejs oparty na Tailwind CSS.

---

## 🛠️ Stack Technologiczny

| Kategoria | Technologie |
| :--- | :--- |
| **Backend** | Python, Flask, Jinja2 |
| **Frontend** | JavaScript (ES6), Tailwind CSS |
| **Dane** | JSON (OCR Blocks Output) |

---

## 🚀 Jak to działa?

1.  **Wybór Szablonu:** Użytkownik wybiera szablon (np. `Umowa.html`). Szablon zawiera tagi:
    ```html
    <span data-keywords="bank, konto">{{ numer_konta }}</span>
    ```
2.  **Analiza Danych:** Aplikacja parsuje plik JSON z OCR (`parsing_res_list`).
3.  **Auto-Uzupełnianie:** System znajduje linię tekstu zawierającą słowo `"konto"` i automatycznie wstawia ją w miejsce `{{ numer_konta }}`.
4.  **Wydruk:** Gotowy plik jest renderowany i drukowany do PDF.

---

<div align="center">
    <sub>Projekt stworzony w celach edukacyjnych.</sub>
</div>
