/* static/js/main.js */

document.addEventListener('DOMContentLoaded', () => {
    initDragAndDrop();           // OCR (Stare)
    initTemplateLogic();         // Szablony (Nowe)
    loadTemplatesList();         // Lista z bazy
});

// --- STARA LOGIKA OCR I ZAKŁADEK (SKRÓCONA DLA CZYTELNOŚCI) ---
function openTab(evt, tabName) {
    let tabcontent = document.getElementsByClassName("tab-content");
    for (let i = 0; i < tabcontent.length; i++) tabcontent[i].classList.remove("active");
    
    let tablinks = document.getElementsByClassName("tab-btn");
    for (let i = 0; i < tablinks.length; i++) {
        tablinks[i].classList.remove("active", "text-white");
        tablinks[i].classList.add("text-slate-400");
    }
    
    document.getElementById(tabName).classList.add("active");
    evt.currentTarget.classList.add("active", "text-white");
    evt.currentTarget.classList.remove("text-slate-400");
}

function initDragAndDrop() { /* ... Twój stary kod do OCR ... */ }
function handleFiles(files) { /* ... Twój stary kod do OCR ... */ }
function toggleAll(source) { /* ... Twój stary kod ... */ }
function handleSelected(action) { /* ... Twój stary kod ... */ }


// ==========================================
// NOWA LOGIKA SZABLONÓW (BEZ TINYMCE)
// ==========================================

// Zmienna globalna przechowująca ostatnią pozycję kursora w dokumencie
let lastRange = null;

function initTemplateLogic() {
    const dropZone = document.getElementById('drop-zone-template');
    const previewArea = document.getElementById('document-preview');

    // 1. Obsługa Drag & Drop pliku DOCX
    if (dropZone) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => { e.preventDefault(); e.stopPropagation(); }, false);
        });
        dropZone.addEventListener('drop', (e) => processTemplateFile(e.dataTransfer.files[0]), false);
    }

    // 2. Śledzenie pozycji kursora
    // Musimy zapamiętać, gdzie użytkownik kliknął, bo kliknięcie w przycisk zmiennej
    // zabierze "focus" z dokumentu.
    if (previewArea) {
        previewArea.addEventListener('keyup', saveCursorPosition);
        previewArea.addEventListener('mouseup', saveCursorPosition);
        // Upewniamy się, że paste wkleja czysty tekst, a nie formatowanie z Worda/Internetu
        previewArea.addEventListener('paste', handleCleanPaste);
    }
}

// Funkcja zapamiętująca gdzie jest kursor
function saveCursorPosition() {
    const selection = window.getSelection();
    if (selection.rangeCount > 0) {
        const range = selection.getRangeAt(0);
        // Sprawdzamy, czy kursor jest wewnątrz naszego dokumentu
        const previewArea = document.getElementById('document-preview');
        if (previewArea && previewArea.contains(range.commonAncestorContainer)) {
            lastRange = range;
        }
    }
}

// Funkcja czyszcząca wklejanie (opcjonalna, ale przydatna)
function handleCleanPaste(e) {
    e.preventDefault();
    const text = (e.originalEvent || e).clipboardData.getData('text/plain');
    document.execCommand('insertText', false, text);
}

// Przetwarzanie DOCX -> HTML (Mammoth)
function processTemplateFile(file) {
    if (!file) return;

    // 1. Ustaw nazwę pliku
    const nameWithoutExt = file.name.replace(/\.[^/.]+$/, "");
    const nameInput = document.getElementById('template-name');
    if (nameInput) nameInput.value = nameWithoutExt;

    const reader = new FileReader();
    reader.onload = function(event) {
        const arrayBuffer = event.target.result;
        mammoth.convertToHtml({arrayBuffer: arrayBuffer})
            .then(result => {
                const previewDiv = document.getElementById('document-preview');
                // Wstawiamy HTML z Mammotha
                previewDiv.innerHTML = result.value;
                
                // 2. ODBLOKOWANIE PANELU ZMIENNYCH (To jest nowość)
                enableVariablePanel();

                console.log("Ostrzeżenia:", result.messages);
            })
            .catch(err => {
                console.error(err);
                alert("Błąd odczytu pliku DOCX.");
            });
    };
    reader.readAsArrayBuffer(file);
}

// Funkcja pomocnicza do odblokowania UI
function enableVariablePanel() {
    const input = document.getElementById('var-name');
    const btn = document.getElementById('add-var-btn');
    
    if(input) {
        input.disabled = false;
        input.placeholder = "np. nazwa_klienta";
        input.focus();
    }
    if(btn) btn.disabled = false;
}

// ==========================================
// WSTAWIANIE ZMIENNYCH (NATIVE JS)
// ==========================================

function insertVariableAtCursor(variableName) {
    const previewArea = document.getElementById('document-preview');
    
    // Jeśli nie mamy zapamiętanej pozycji, spróbujmy wstawić na koniec
    if (!lastRange) {
        previewArea.focus();
        // Ustaw kursor na koniec
        const selection = window.getSelection();
        selection.selectAllChildren(previewArea);
        selection.collapseToEnd();
        lastRange = selection.getRangeAt(0);
    }

    // Odtwórz zaznaczenie
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(lastRange);

    // Stwórz element HTML dla zmiennej
    // contenteditable="false" jest kluczowe - traktuje zmienną jak jeden blok, którego nie da się edytować w środku
    const badge = document.createElement('span');
    badge.className = 'variable-badge'; 
    badge.contentEditable = "false"; 
    badge.innerText = `{{ ${variableName} }}`;

    // Wstaw element w miejsce kursora
    lastRange.deleteContents(); // Usuń jeśli coś było zaznaczone
    lastRange.insertNode(badge);
    
    // Dodaj spację po zmiennej, żeby łatwiej się pisało dalej
    const space = document.createTextNode('\u00A0');
    lastRange.setStartAfter(badge);
    lastRange.insertNode(space);
    
    // Przesuń kursor ZA spację
    lastRange.setStartAfter(space);
    lastRange.collapse(true);
    selection.removeAllRanges();
    selection.addRange(lastRange);

    // Zaktualizuj lastRange
    saveCursorPosition();
}

function addNewVariable() {
    const input = document.getElementById('var-name');
    // Zabezpieczenie: nie dodawaj, jeśli input jest zablokowany (dokument nie wgrany)
    if (input.disabled) return; 

    const name = input.value.trim().replace(/\s+/g, '_').toLowerCase(); 
    if (!name) return;

    const list = document.getElementById('variables-list');
    
    // Kontener dla przycisku wstawiania i usuwania
    const container = document.createElement('div');
    container.className = "flex items-center gap-2 group animate-fade-in-up";

    // 1. Przycisk wstawiania (Lewa część)
    const insertBtn = document.createElement('button');
    insertBtn.className = "flex-1 text-left text-sm p-3 bg-slate-700 border border-slate-600 hover:border-indigo-500 rounded-lg text-indigo-300 font-mono font-bold transition-all flex justify-between items-center";
    insertBtn.innerHTML = `<span>{{ ${name} }}</span> <span class="text-xs text-slate-500 opacity-0 group-hover:opacity-100 transition-opacity">Wstaw &rarr;</span>`;
    insertBtn.onclick = function() { insertVariableAtCursor(name); };

    // 2. Przycisk usuwania (Prawa część - Kosz)
    const deleteBtn = document.createElement('button');
    deleteBtn.className = "p-3 bg-slate-800 border border-slate-700 hover:bg-red-900/50 hover:border-red-500 hover:text-red-400 rounded-lg text-slate-500 transition-all";
    deleteBtn.innerHTML = `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>`;
    
    // Logika usuwania
    deleteBtn.onclick = function() {
        container.remove();
    };

    container.appendChild(insertBtn);
    container.appendChild(deleteBtn);
    list.appendChild(container);

    input.value = '';
}

// ==========================================
// ZAPIS (WYSŁANIE SAMEGO HTML)
// ==========================================

function saveTemplate() {
    const previewDiv = document.getElementById('document-preview');
    if (!previewDiv) return;

    const htmlContent = previewDiv.innerHTML;
    const nameInput = document.getElementById('template-name');
    const name = nameInput ? nameInput.value : "szablon";

    fetch('/save_template_html', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name, html: htmlContent })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            alert("Szablon zapisany!");
            loadTemplatesList();
        } else {
            alert("Błąd: " + data.error);
        }
    })
    .catch(err => console.error(err));
}

function loadTemplatesList() {
    const container = document.getElementById('templates-list-container');
    if(container) {
        fetch('/templates_list_html').then(r => r.text()).then(html => container.innerHTML = html);
    }
}


// ==========================================
// CZĘŚĆ 4: GENEROWANIE DOKUMENTÓW (TAB 3)
// ==========================================

// 1. Załaduj listę szablonów do selecta
function loadTemplatesForSelect() {
    const select = document.getElementById('template-select');
    if (!select) return;

    fetch('/templates_list_html') // Używamy tego samego endpointu co wcześniej, ale parsujemy go ręcznie lub tworzymy nowy endpoint JSON
    // UWAGA: Twój obecny endpoint zwraca HTML. Dla czystości lepiej byłoby, gdyby zwracał JSON. 
    // Ale poradzimy sobie parsując nazwy plików z folderu /templates_db (backend).
    // Załóżmy dla uproszczenia, że zrobisz endpoint zwracający JSON z nazwami plików.
    
    // TYMCZASOWE ROZWIĄZANIE (fetch listy plików HTML):
    // Zróbmy prosty endpoint w Flask, który zwróci JSON, dodaj to do app.py (kod poniżej).
    
    .then(() => fetch('/api/get_templates_json')) 
    .then(r => r.json())
    .then(files => {
        select.innerHTML = '<option value="" disabled selected>-- Wybierz z listy --</option>';
        files.forEach(file => {
            const option = document.createElement('option');
            option.value = file;
            option.text = file.replace('.html', '').replace(/_/g, ' ');
            select.appendChild(option);
        });
    });
}

// 2. Wczytaj wybrany szablon i zbuduj formularz
function loadSelectedTemplate(filename) {
    if (!filename) return;

    // Pobieramy treść HTML szablonu (musisz mieć endpoint do serwowania plików z folderu templates_db)
    fetch(`/get_template_content/${filename}`)
        .then(r => r.text())
        .then(html => {
            // 1. Wstaw podgląd
            const preview = document.getElementById('readonly-preview');
            preview.innerHTML = html;

            // 2. Zbuduj formularz
            buildDynamicForm(html);
        })
        .catch(err => console.error("Błąd ładowania szablonu:", err));
}

// 3. Budowanie formularza na podstawie zmiennych {{ ... }}
function buildDynamicForm(htmlContent) {
    const container = document.getElementById('dynamic-form-container');
    container.innerHTML = '';

    // Regex szukający wzorca {{ nazwa_zmiennej }}
    // Flaga 'g' szuka wszystkich wystąpień
    const regex = /\{\{\s*([a-zA-Z0-9_ąęćłńóśźżĄĘĆŁŃÓŚŹŻ]+)\s*\}\}/g;
    
    // Używamy Set, aby unikać duplikatów (np. jak data występuje 3 razy, chcemy 1 input)
    const foundVariables = new Set();
    let match;

    while ((match = regex.exec(htmlContent)) !== null) {
        // match[1] to nazwa zmiennej bez nawiasów klamrowych
        foundVariables.add(match[1]);
    }

    if (foundVariables.size === 0) {
        container.innerHTML = '<p class="text-slate-400 text-sm text-center">Ten szablon nie ma zmiennych do uzupełnienia.</p>';
        return;
    }

    // Generujemy inputy
    foundVariables.forEach(varName => {
        // Ładna etykieta (zamiana _ na spację, duża litera)
        const labelText = varName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

        const wrapper = document.createElement('div');
        wrapper.className = "group";

        const label = document.createElement('label');
        label.className = "block text-xs font-bold text-slate-400 mb-1 group-focus-within:text-indigo-400 transition-colors";
        label.innerText = labelText;

        const input = document.createElement('input');
        input.type = "text";
        input.name = varName; // Ważne dla zbierania danych
        input.className = "w-full bg-slate-900 border border-slate-600 text-white text-sm rounded-lg p-2.5 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none transition-all placeholder-slate-600";
        input.placeholder = `Wpisz ${labelText}...`;
        
        // Live update podglądu (opcjonalne, ale fajne!)
        input.addEventListener('input', (e) => updatePreview(varName, e.target.value));

        wrapper.appendChild(label);
        wrapper.appendChild(input);
        container.appendChild(wrapper);
    });
}

// 4. Aktualizacja podglądu na żywo (opcjonalne)
function updatePreview(varName, value) {
    // To jest trickowe, bo w HTML mamy {{ varName }}. 
    // Najprościej byłoby podmieniać w locie, ale to zniszczy oryginalne "znaczniki" dla przyszłych edycji w tej sesji.
    // Lepsze podejście dla "Read Only": Znajdź wszystkie spany, które zawierają ten tekst.
    
    // W naszym edytorze zmienne są w <span class="variable-badge">...</span> lub w tekście.
    // Dla prostoty w tym przykładzie: nie robimy live update na "tekście", 
    // bo musielibyśmy parsować HTML w kółko. 
    // Zostawmy podgląd statyczny z widocznymi {{ ... }} jako "szablon",
    // a użytkownik widzi co wpisuje w formularzu.
    
    // Jeśli jednak bardzo chcesz live preview, musisz trzymać oryginalny HTML w pamięci
    // i przy każdej zmianie robić .replace() i wrzucać do diva.
}

// 5. Finalne Generowanie
function generateFinalDocument() {
    // Zbierz dane z formularza
    const inputs = document.querySelectorAll('#dynamic-form-container input');
    const formData = {};
    
    inputs.forEach(input => {
        formData[input.name] = input.value;
    });

    const templateName = document.getElementById('template-select').value;
    if(!templateName) {
        alert("Wybierz szablon!");
        return;
    }

    console.log("Wysyłanie danych:", formData);

    // Wyślij do Flask
    fetch('/generate_document', { // Nowy endpoint w Pythonie
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            template: templateName,
            data: formData
        })
    })
    .then(r => r.blob()) // Oczekujemy pliku (PDF/DOCX)
    .then(blob => {
        // Pobierz plik
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = "gotowy_dokument.pdf"; // lub .docx
        document.body.appendChild(a);
        a.click();
        a.remove();
    })
    .catch(err => {
        console.error(err);
        alert("Błąd generowania dokumentu.");
    });
}

// Wywołaj przy starcie (lub przy przełączeniu na zakładkę 'generate')
document.addEventListener('DOMContentLoaded', () => {
    // ... inne inicjalizacje
    loadTemplatesForSelect();
});

function generateFinalDocument() {
    // 1. Zbierz dane z formularza
    const inputs = document.querySelectorAll('#dynamic-form-container input');
    const formData = {};
    
    inputs.forEach(input => {
        formData[input.name] = input.value;
    });

    const templateName = document.getElementById('template-select').value;
    if(!templateName) {
        alert("Wybierz szablon!");
        return;
    }

    // 2. Wyślij do Flask
    fetch('/generate_document', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            template: templateName,
            data: formData
        })
    })
    .then(response => {
        if (!response.ok) throw new Error("Błąd generowania");
        return response.text(); // Odbieramy jako tekst HTML
    })
    .then(htmlText => {
        // 3. Otwórz w nowym oknie i wydrukuj
        const printWindow = window.open('', '_blank');
        printWindow.document.write(htmlText);
        printWindow.document.close(); // Ważne dla niektórych przeglądarek
        
        // Stylizacja okna drukowania (opcjonalnie, żeby Tailwind działał w nowym oknie)
        // Musimy upewnić się, że Tailwind jest załadowany w nowym oknie
        const tailwindLink = printWindow.document.createElement('script');
        tailwindLink.src = "https://cdn.tailwindcss.com";
        printWindow.document.head.appendChild(tailwindLink);
    })
    .catch(err => {
        console.error(err);
        alert("Błąd generowania dokumentu.");
    });
}