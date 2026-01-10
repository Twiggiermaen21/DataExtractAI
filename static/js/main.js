/* static/js/main.js */
let globalClientsData = []; // Tutaj przechowamy pobrane dane
document.addEventListener('DOMContentLoaded', () => {
    // 1. Inicjalizacja starych funkcji (OCR, Drag&Drop)
    initDragAndDrop();
    
    // 2. Inicjalizacja nowej logiki szablonów
    initTemplateLogic();
    
    // 3. Ładowanie listy szablonów do selecta
    loadTemplatesForSelect();
// NOWE: Ładowanie danych do selecta importu
    loadClientsForImport();
    // 4. GLOBALNY NASŁUCHIWACZ LIVE PREVIEW (To naprawia automatyczne odświeżanie)
    const formContainer = document.getElementById('dynamic-form-container');
    if (formContainer) {
        formContainer.addEventListener('input', function(e) {
            // Sprawdzamy, czy zdarzenie pochodzi z inputa
            if (e.target && e.target.matches('input')) {
                updatePreview(e.target.name, e.target.value);
            }
        });
    }
});

// ==========================================
// STARA LOGIKA OCR I ZAKŁADEK
// ==========================================
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
// NOWA LOGIKA TWORZENIA SZABLONÓW (KREATOR)
// ==========================================

let lastRange = null;

function initTemplateLogic() {
    const dropZone = document.getElementById('drop-zone-template');
    const previewArea = document.getElementById('document-preview');

    // Obsługa Drag & Drop pliku DOCX
    if (dropZone) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => { e.preventDefault(); e.stopPropagation(); }, false);
        });
        dropZone.addEventListener('drop', (e) => processTemplateFile(e.dataTransfer.files[0]), false);
    }

    // Śledzenie pozycji kursora
    if (previewArea) {
        previewArea.addEventListener('keyup', saveCursorPosition);
        previewArea.addEventListener('mouseup', saveCursorPosition);
        previewArea.addEventListener('paste', handleCleanPaste);
    }
}

function saveCursorPosition() {
    const selection = window.getSelection();
    if (selection.rangeCount > 0) {
        const range = selection.getRangeAt(0);
        const previewArea = document.getElementById('document-preview');
        if (previewArea && previewArea.contains(range.commonAncestorContainer)) {
            lastRange = range;
        }
    }
}

function handleCleanPaste(e) {
    e.preventDefault();
    const text = (e.originalEvent || e).clipboardData.getData('text/plain');
    document.execCommand('insertText', false, text);
}

function processTemplateFile(file) {
    if (!file) return;

    const nameWithoutExt = file.name.replace(/\.[^/.]+$/, "");
    const nameInput = document.getElementById('template-name');
    if (nameInput) nameInput.value = nameWithoutExt;

    const reader = new FileReader();
    reader.onload = function(event) {
        const arrayBuffer = event.target.result;
        mammoth.convertToHtml({arrayBuffer: arrayBuffer})
            .then(result => {
                const previewDiv = document.getElementById('document-preview');
                previewDiv.innerHTML = result.value;
                enableVariablePanel();
            })
            .catch(err => {
                console.error(err);
                alert("Błąd odczytu pliku DOCX.");
            });
    };
    reader.readAsArrayBuffer(file);
}

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

function insertVariableAtCursor(variableName) {
    const previewArea = document.getElementById('document-preview');
    if (!lastRange) {
        previewArea.focus();
        const selection = window.getSelection();
        selection.selectAllChildren(previewArea);
        selection.collapseToEnd();
        lastRange = selection.getRangeAt(0);
    }

    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(lastRange);

    const badge = document.createElement('span');
    badge.className = 'variable-badge'; 
    badge.contentEditable = "false"; 
    badge.innerText = `{{ ${variableName} }}`;

    lastRange.deleteContents();
    lastRange.insertNode(badge);
    
    const space = document.createTextNode('\u00A0');
    lastRange.setStartAfter(badge);
    lastRange.insertNode(space);
    
    lastRange.setStartAfter(space);
    lastRange.collapse(true);
    selection.removeAllRanges();
    selection.addRange(lastRange);

    saveCursorPosition();
}

function addNewVariable() {
    const input = document.getElementById('var-name');
    if (input.disabled) return; 

    const name = input.value.trim().replace(/\s+/g, '_').toLowerCase(); 
    if (!name) return;

    const list = document.getElementById('variables-list');
    const container = document.createElement('div');
    container.className = "flex items-center gap-2 group animate-fade-in-up";

    const insertBtn = document.createElement('button');
    insertBtn.className = "flex-1 text-left text-sm p-3 bg-slate-700 border border-slate-600 hover:border-indigo-500 rounded-lg text-indigo-300 font-mono font-bold transition-all flex justify-between items-center";
    insertBtn.innerHTML = `<span>{{ ${name} }}</span> <span class="text-xs text-slate-500 opacity-0 group-hover:opacity-100 transition-opacity">Wstaw &rarr;</span>`;
    insertBtn.onclick = function() { insertVariableAtCursor(name); };

    const deleteBtn = document.createElement('button');
    deleteBtn.className = "p-3 bg-slate-800 border border-slate-700 hover:bg-red-900/50 hover:border-red-500 hover:text-red-400 rounded-lg text-slate-500 transition-all";
    deleteBtn.innerHTML = `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>`;
    deleteBtn.onclick = function() { container.remove(); };

    container.appendChild(insertBtn);
    container.appendChild(deleteBtn);
    list.appendChild(container);

    input.value = '';
}

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
            loadTemplatesList(); // Jeśli masz tę funkcję do odświeżania listy
        } else {
            alert("Błąd: " + data.error);
        }
    })
    .catch(err => console.error(err));
}

function loadTemplatesList() {
    // Tutaj możesz dodać logikę odświeżania listy szablonów w kreatorze, jeśli jest potrzebna
}


// ==========================================
// CZĘŚĆ 4: GENEROWANIE DOKUMENTÓW I LIVE PREVIEW
// ==========================================

// 1. Załaduj listę szablonów do selecta
function loadTemplatesForSelect() {
    const select = document.getElementById('template-select');
    if (!select) return;

    fetch('/api/get_templates_json') // Upewnij się, że masz ten endpoint w Pythonie
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

// 2. Wczytaj wybrany szablon, zbuduj formularz i włącz Live Preview
function loadSelectedTemplate(filename) {
    if (!filename) return;

    fetch(`/get_template_content/${filename}`)
        .then(r => r.text())
        .then(rawHtml => {
            // KROK A: Budujemy formularz na podstawie "czystego" HTML (żeby regex łatwo znalazł zmienne)
            buildDynamicForm(rawHtml);

            // KROK B: Przygotowanie HTML do Live Preview
            // Zamieniamy {{ zmienna }} na <span data-bind="zmienna">...</span>
            // Dzięki temu JavaScript wie, co aktualizować
            const liveHtml = rawHtml.replace(
                /\{\{\s*([a-zA-Z0-9_ąęćłńóśźżĄĘĆŁŃÓŚŹŻ]+)\s*\}\}/g, 
                (match, varName) => {
                    return `<span data-bind="${varName}" class="live-var bg-yellow-200/50 px-1 rounded transition-colors">${match}</span>`;
                }
            );

            // KROK C: Wstawiamy "uzbrojony" HTML do podglądu
            const preview = document.getElementById('readonly-preview');
            preview.innerHTML = liveHtml;
        })
        .catch(err => console.error("Błąd ładowania szablonu:", err));
}

// 3. Budowanie formularza (Inputy)
function buildDynamicForm(htmlContent) {
    const container = document.getElementById('dynamic-form-container');
    container.innerHTML = '';

    const regex = /\{\{\s*([a-zA-Z0-9_ąęćłńóśźżĄĘĆŁŃÓŚŹŻ]+)\s*\}\}/g;
    const foundVariables = new Set();
    let match;

    while ((match = regex.exec(htmlContent)) !== null) {
        foundVariables.add(match[1]);
    }

    if (foundVariables.size === 0) {
        container.innerHTML = '<p class="text-slate-400 text-sm text-center">Ten szablon nie ma zmiennych do uzupełnienia.</p>';
        return;
    }

    foundVariables.forEach(varName => {
        const labelText = varName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

        const wrapper = document.createElement('div');
        wrapper.className = "group mb-4";

        const label = document.createElement('label');
        label.className = "block text-xs font-bold text-slate-400 mb-1 group-focus-within:text-indigo-400 transition-colors";
        label.innerText = labelText;

        const input = document.createElement('input');
        input.type = "text";
        input.name = varName; // Musi pasować do data-bind
        input.className = "w-full bg-slate-900 border border-slate-600 text-white text-sm rounded-lg p-2.5 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none transition-all placeholder-slate-600";
        input.placeholder = `Wpisz ${labelText}...`;
        input.autocomplete = "off";

        wrapper.appendChild(label);
        wrapper.appendChild(input);
        container.appendChild(wrapper);
    });
}

// 4. Funkcja aktualizująca podgląd (wywoływana przez globalny nasłuchiwacz)
function updatePreview(varName, value) {
    const targets = document.querySelectorAll(`[data-bind="${varName}"]`);

    targets.forEach(el => {
        if (value && value.trim() !== "") {
            // Użytkownik wpisał tekst -> wstawiamy go i usuwamy tło
            el.textContent = value;
            el.classList.remove('bg-yellow-200/50'); 
            el.classList.add('bg-transparent', 'text-indigo-700', 'font-medium'); // Opcjonalnie: kolor tekstu
        } else {
            // Pole puste -> przywracamy {{ zmienna }} i tło
            el.textContent = `{{ ${varName} }}`; 
            el.classList.add('bg-yellow-200/50');
            el.classList.remove('bg-transparent', 'text-indigo-700', 'font-medium');
        }
    });
}

// 5. Finalne Generowanie Dokumentu (Pobieranie PDF/DOCX)
function generateFinalDocument() {
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

    fetch('/generate_document', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            template: templateName,
            data: formData
        })
    })
    .then(r => r.blob())
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Dokument_${templateName.replace('.html','')}.pdf`; // Domyślnie PDF
        document.body.appendChild(a);
        a.click();
        a.remove();
    })
    .catch(err => {
        console.error(err);
        alert("Błąd generowania dokumentu.");
    });
}

// ==========================================
// IMPORT DANYCH Z BAZY (JSON)
// ==========================================

// 1. Pobierz dane z backendu (lub pliku JSON)
function loadClientsForImport() {
    const select = document.getElementById('data-import-select');
    if (!select) return;

    // Załóżmy, że masz endpoint /api/get_clients_json
    // Jeśli testujesz lokalnie, możesz tu wpisać dane "na sztywno" zamiast fetch
    fetch('/api/get_clients_json') 
        .then(r => r.json())
        .then(data => {
            globalClientsData = data; // Zapisz w zmiennej globalnej
            
            select.innerHTML = '<option value="" disabled selected>-- Wybierz klienta --</option>';
            
            data.forEach((item, index) => {
                const option = document.createElement('option');
                // Używamy indexu tablicy jako value, żeby łatwo znaleźć obiekt
                option.value = index; 
                // Wyświetlamy nazwę (dostosuj pole np. item.nazwa_firmy)
                option.text = item.nazwa || item.imie_nazwisko || `Klient #${index + 1}`;
                select.appendChild(option);
            });
        })
        .catch(err => console.error("Błąd pobierania klientów:", err));
}

// 2. Wypełnij formularz po wybraniu z listy
function fillFormData(selectedIndex) {
    if (selectedIndex === "") return;

    // Pobierz obiekt danych dla wybranego klienta
    const selectedData = globalClientsData[selectedIndex];
    if (!selectedData) return;

    // Znajdź wszystkie aktywne inputy w formularzu
    const inputs = document.querySelectorAll('#dynamic-form-container input');

    inputs.forEach(input => {
        const fieldName = input.name; // np. "miasto", "nip"

        // Sprawdź, czy w JSONie klienta istnieje taki klucz
        if (selectedData.hasOwnProperty(fieldName)) {
            // 1. Wstaw wartość
            input.value = selectedData[fieldName];

            // 2. KLUCZOWE: Wymuś zdarzenie 'input', aby zadziałał Live Preview!
            // Bez tego input się wypełni, ale podgląd dokumentu się nie odświeży.
            input.dispatchEvent(new Event('input', { bubbles: true }));
            
            // Efekt wizualny (mignięcie na zielono) że dane weszły
            input.classList.add('ring-2', 'ring-emerald-500');
            setTimeout(() => input.classList.remove('ring-2', 'ring-emerald-500'), 500);
        }
    });
}

function loadOutputData() {
    const select = document.getElementById('data-import-select');
    if (!select) return;

    fetch('/api/get_output_data') // Endpoint z Kroku 1
        .then(r => r.json())
        .then(data => {
            globalOutputData = data; // Zapisujemy dane w pamięci przeglądarki
            
            select.innerHTML = '<option value="" disabled selected>-- Wybierz dane do wstawienia --</option>';
            
            if (data.length === 0) {
                const option = document.createElement('option');
                option.text = "(Brak danych w folderze output)";
                select.appendChild(option);
                return;
            }

            data.forEach((item, index) => {
                const option = document.createElement('option');
                option.value = index; // Jako value używamy indeksu tablicy (0, 1, 2...)
                
                // Próbujemy zgadnąć, co wyświetlić jako nazwę w liście (np. nazwa firmy, imię, albo ID)
                // Dostosuj te pola do swojego JSONa!
                const label = item.nazwa || item.nazwa_firmy || item.imie_nazwisko || item.klient || `Rekord #${index + 1}`;
                
                option.text = label;
                select.appendChild(option);
            });
        })
        .catch(err => console.error("Błąd ładowania danych z output:", err));
}

function fillFormData(selectedIndex) {
    if (selectedIndex === "") return;

    // Pobieramy odpowiedni obiekt z pamięci
    const dataRow = globalOutputData[selectedIndex];
    if (!dataRow) return;

    // Znajdujemy wszystkie inputy w formularzu
    const inputs = document.querySelectorAll('#dynamic-form-container input');

    inputs.forEach(input => {
        const fieldName = input.name; // np. "miasto", "nip"

        // Jeśli w JSONie istnieje klucz o takiej samej nazwie jak input...
        if (dataRow.hasOwnProperty(fieldName)) {
            // 1. Wstaw wartość
            input.value = dataRow[fieldName];

            // 2. KLUCZOWE: Symulujemy wpisywanie tekstu, żeby zadziałał Live Preview
            input.dispatchEvent(new Event('input', { bubbles: true }));

            // 3. Efekt wizualny (mignięcie na zielono)
            input.classList.add('ring-2', 'ring-emerald-500', 'transition-all', 'duration-500');
            setTimeout(() => {
                input.classList.remove('ring-2', 'ring-emerald-500');
            }, 1000);
        }
    });
}