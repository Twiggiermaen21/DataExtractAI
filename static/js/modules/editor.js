/* static/js/modules/editor.js */

let lastRange = null;

export function initTemplateEditor() {
    const dropZone = document.getElementById('drop-zone-template');
    const previewArea = document.getElementById('document-preview');

    // Obsługa Drag & Drop
    if (dropZone) {
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            e.stopPropagation();
            processTemplateFile(e.dataTransfer.files[0]);
        });
        
        ['dragenter', 'dragover', 'dragleave'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });
    }

    // Nasłuchiwanie pozycji kursora
    if (previewArea) {
        previewArea.addEventListener('keyup', saveCursorPosition);
        previewArea.addEventListener('mouseup', saveCursorPosition);
        previewArea.addEventListener('click', saveCursorPosition);
        
        previewArea.addEventListener('paste', (e) => {
            e.preventDefault();
            const text = (e.originalEvent || e).clipboardData.getData('text/plain');
            document.execCommand('insertText', false, text);
        });
    }

    // Eksport funkcji do window
    window.saveTemplate = saveTemplate;
    window.addNewVariable = addNewVariable;
    window.processTemplateFile = processTemplateFile;
    window.insertVariableAtCursor = insertVariableAtCursor;
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
    const inputName = document.getElementById('var-name');
    const inputKeywords = document.getElementById('var-keywords');
    const btn = document.getElementById('add-var-btn');
    
    if(inputName) {
        inputName.disabled = false;
        inputName.focus();
    }
    if(inputKeywords) inputKeywords.disabled = false;
    if(btn) btn.disabled = false;
}

function addNewVariable() {
    const inputName = document.getElementById('var-name');
    const inputKeywords = document.getElementById('var-keywords');
    
    if (inputName.disabled) return; 

    const rawName = inputName.value.trim();
    if (!rawName) return;
    
    const name = rawName.replace(/\s+/g, '_').toLowerCase(); 
    const keywords = inputKeywords.value.trim(); // Pobieramy słowa kluczowe

    const list = document.getElementById('variables-list');
    const container = document.createElement('div');
    container.className = "flex items-center gap-2 group animate-fade-in-up mb-2";

    // Przycisk wstawiania
    const insertBtn = document.createElement('button');
    insertBtn.className = "flex-1 text-left p-3 bg-slate-700 border border-slate-600 hover:border-indigo-500 rounded-lg text-indigo-300 transition-all flex flex-col";
    
    // HTML przycisku z opcjonalnymi słowami kluczowymi
    let btnContent = `<div class="flex justify-between items-center w-full">
                        <span class="font-mono font-bold text-sm">{{ ${name} }}</span>
                        <span class="text-xs text-slate-500 opacity-0 group-hover:opacity-100 transition-opacity">Wstaw &rarr;</span>
                      </div>`;
    
    if (keywords) {
        btnContent += `<span class="text-[10px] text-slate-500 mt-1 truncate max-w-[150px]" title="${keywords}">🏷️ ${keywords}</span>`;
    }

    insertBtn.innerHTML = btnContent;
    
    // Kliknięcie przekazuje również keywords do funkcji wstawiania
    insertBtn.onclick = function() { insertVariableAtCursor(name, keywords); };

    // Przycisk usuwania
    const deleteBtn = document.createElement('button');
    deleteBtn.className = "p-3 h-full bg-slate-800 border border-slate-700 hover:bg-red-900/50 hover:border-red-500 hover:text-red-400 rounded-lg text-slate-500 transition-all flex items-center justify-center";
    deleteBtn.innerHTML = `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>`;
    deleteBtn.onclick = function() { container.remove(); };

    container.appendChild(insertBtn);
    container.appendChild(deleteBtn);
    list.appendChild(container);

    // Reset formularza
    inputName.value = '';
    inputKeywords.value = '';
    inputName.focus();
}

function insertVariableAtCursor(variableName, keywords = "") {
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
    badge.className = 'variable-token inline-block  text-indigo-900 px-2 py-0.5 rounded border border-indigo-700 mx-1 font-mono text-sm select-all'; 
    badge.contentEditable = "false"; 
    badge.innerText = `{{ ${variableName} }}`;
    
    // KLUCZOWA ZMIANA: Zapisujemy słowa kluczowe w atrybucie HTML
    if (keywords) {
        badge.setAttribute('data-keywords', keywords);
        badge.title = `Słowa kluczowe: ${keywords}`; // Tooltip po najechaniu myszką w edytorze
    }

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
            alert("Szablon zapisany pomyślnie!");
        } else {
            alert("Błąd zapisu: " + data.error);
        }
    })
    .catch(err => console.error(err));
}