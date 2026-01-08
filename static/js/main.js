/* static/js/main.js */

document.addEventListener('DOMContentLoaded', () => {
    // Inicjalizacja Drag & Drop po załadowaniu strony
    initDragAndDrop();
});

// --- 1. Obsługa Zakładek ---
function openTab(evt, tabName) {
    let i, tabcontent, tablinks;
    
    // Ukryj wszystkie treści
    tabcontent = document.getElementsByClassName("tab-content");
    for (i = 0; i < tabcontent.length; i++) {
        tabcontent[i].classList.remove("active");
    }
    
    // Zresetuj style przycisków
    tablinks = document.getElementsByClassName("tab-btn");
    for (i = 0; i < tablinks.length; i++) {
        tablinks[i].classList.remove("active", "text-blue-400");
        tablinks[i].classList.add("text-slate-400");
    }
    
    // Pokaż wybrany
    document.getElementById(tabName).classList.add("active");
    evt.currentTarget.classList.add("active");
    evt.currentTarget.classList.remove("text-slate-400");
}

// --- 2. LOGIKA UPLOAD ---

function initDragAndDrop() {
    const dropZone = document.getElementById('drop-zone');
    if (!dropZone) return;

    // Obsługa zdarzeń Drag & Drop
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) { e.preventDefault(); e.stopPropagation(); }

    ['dragenter', 'dragover'].forEach(() => dropZone.classList.add('drag-active'));
    ['dragleave', 'drop'].forEach(() => dropZone.classList.remove('drag-active'));

    dropZone.addEventListener('drop', (e) => handleFiles(e.dataTransfer.files), false);
}

// Główna funkcja wysyłająca
function handleFiles(files) {
    if (!files || files.length === 0) return;

    const loadingOverlay = document.getElementById('loading-overlay');
    const filesListContainer = document.getElementById('files-list-container');

    // Pokaż spinner
    if(loadingOverlay) {
        loadingOverlay.classList.remove('hidden');
        loadingOverlay.classList.add('flex');
    }

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append('file', files[i]);
    }

    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            return fetch('/files_list_html');
        } else {
            alert('Błąd uploadu: ' + JSON.stringify(data));
            throw new Error('Upload failed');
        }
    })
    .then(response => response.text())
    .then(html => {
        if(filesListContainer) filesListContainer.innerHTML = html;
    })
    .catch(error => {
        console.error('Błąd:', error);
    })
    .finally(() => {
        if(loadingOverlay) {
            loadingOverlay.classList.add('hidden');
            loadingOverlay.classList.remove('flex');
        }
    });
}

// --- 3. OBSŁUGA ZAZNACZANIA (CHECKBOXY) ---

function toggleAll(source) {
    const checkboxes = document.querySelectorAll('.file-checkbox');
    for(let i=0; i<checkboxes.length; i++) {
        checkboxes[i].checked = source.checked;
    }
}

function handleSelected(action) {
    const checkboxes = document.querySelectorAll('.file-checkbox:checked');
    const files = Array.from(checkboxes).map(cb => cb.value);
    const loadingOverlay = document.getElementById('loading-overlay');

    if (files.length === 0) {
        alert("Nie zaznaczono żadnych plików.");
        return;
    }

    if (action === 'delete' && !confirm(`Czy na pewno chcesz usunąć ${files.length} plików?`)) {
        return;
    }

    if(loadingOverlay) {
        loadingOverlay.classList.remove('hidden');
        loadingOverlay.classList.add('flex');
    }

    const endpoint = action === 'ocr' ? '/process_selected' : '/delete_selected';

    fetch(endpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ files: files }),
    })
    .then(response => response.json())
    .then(data => {
        return fetch('/files_list_html');
    })
    .then(response => response.text())
    .then(html => {
        document.getElementById('files-list-container').innerHTML = html;
        if (action === 'ocr') {
            window.location.reload(); 
        }
    })
    .catch((error) => {
        console.error('Error:', error);
        alert("Wystąpił błąd.");
    })
    .finally(() => {
        if(loadingOverlay) {
            loadingOverlay.classList.add('hidden');
            loadingOverlay.classList.remove('flex');
        }
        // Odznacz "Zaznacz wszystko"
        const toggleAllBox = document.querySelector('input[onchange="toggleAll(this)"]');
        if(toggleAllBox) toggleAllBox.checked = false;
    });
}


// --- 4. OBSŁUGA SZABLONÓW (Nowa sekcja) ---

document.addEventListener('DOMContentLoaded', () => {
    // Inicjalizacja Drop Zone dla faktur (stary kod)
    initDragAndDrop(); 
    
    // Inicjalizacja Drop Zone dla szablonów (NOWY KOD)
    initTemplateDragAndDrop();
    
    // Załaduj listę szablonów przy starcie
    loadTemplatesList();
});

function initTemplateDragAndDrop() {
    const dropZone = document.getElementById('drop-zone-template');
    if (!dropZone) return;

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => { e.preventDefault(); e.stopPropagation(); }, false);
    });

    // Stylizacja przy najechaniu (inny kolor dla szablonów - indigo)
    ['dragenter', 'dragover'].forEach(() => {
        dropZone.classList.add('border-indigo-500', 'bg-indigo-900/10');
    });

    ['dragleave', 'drop'].forEach(() => {
        dropZone.classList.remove('border-indigo-500', 'bg-indigo-900/10');
    });

    dropZone.addEventListener('drop', (e) => handleTemplates(e.dataTransfer.files), false);
}

function handleTemplates(files) {
    if (!files || files.length === 0) return;

    const loadingOverlay = document.getElementById('loading-overlay-template');
    
    if(loadingOverlay) {
        loadingOverlay.classList.remove('hidden');
        loadingOverlay.classList.add('flex');
    }

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append('file', files[i]);
    }

    fetch('/upload_template', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            return loadTemplatesList(); // Odśwież listę
        } else {
            alert('Błąd uploadu: ' + JSON.stringify(data));
        }
    })
    .catch(error => console.error('Błąd:', error))
    .finally(() => {
        if(loadingOverlay) {
            loadingOverlay.classList.add('hidden');
            loadingOverlay.classList.remove('flex');
        }
    });
}

function loadTemplatesList() {
    return fetch('/templates_list_html')
        .then(response => response.text())
        .then(html => {
            const container = document.getElementById('templates-list-container');
            if(container) container.innerHTML = html;
        });
}