/* static/js/modules/ocr.js */

export function initOCR() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('invoice-upload');

    // 1. Obsługa Drag & Drop (wizualna)
    if (dropZone) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => dropZone.classList.add('border-blue-500', 'bg-slate-700'), false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => dropZone.classList.remove('border-blue-500', 'bg-slate-700'), false);
        });

        dropZone.addEventListener('drop', handleDrop, false);
    }

    // 2. Eksport funkcji do globalnego zakresu (window), 
    // aby działały przyciski w HTML (onclick="handleFiles(...)")
    window.handleFiles = handleFiles;
    window.handleSelected = handleSelected;
    
    // Załadowanie listy plików przy starcie
    refreshFilesList();
}

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    handleFiles(files);
}

// Główna funkcja wysyłająca pliki na serwer
function handleFiles(files) {
    if (!files.length) return;

    const formData = new FormData();
    // Konwersja FileList na tablicę
    ([...files]).forEach(file => {
        formData.append('file', file);
    });

    // Pokazanie loadera (jeśli istnieje w HTML)
    const loader = document.getElementById('loading-overlay');
    if (loader) loader.classList.remove('hidden');

    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log(`Wgrano ${data.count} plików.`);
            refreshFilesList();
        } else {
            alert('Błąd uploadu: ' + data.error);
        }
    })
    .catch(error => console.error('Error:', error))
    .finally(() => {
        if (loader) loader.classList.add('hidden');
    });
}

// Funkcja odświeżająca listę plików (pobiera HTML z serwera)
function refreshFilesList() {
    fetch('/files_list_html')
        .then(response => response.text())
        .then(html => {
            const container = document.getElementById('files-list-container');
            if (container) container.innerHTML = html;
        });
}

// Obsługa przycisków "OCR Zaznaczone" i "Usuń Zaznaczone"
function handleSelected(action) {
    // Pobieramy zaznaczone checkboxy
    const checkboxes = document.querySelectorAll('.file-checkbox:checked');
    const selectedFiles = Array.from(checkboxes).map(cb => cb.value);

    if (selectedFiles.length === 0) {
        alert("Zaznacz najpierw pliki na liście.");
        return;
    }

    if (action === 'delete') {
        if (!confirm(`Czy na pewno usunąć ${selectedFiles.length} plików?`)) return;
        
        fetch('/delete_selected', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ files: selectedFiles })
        })
        .then(r => r.json())
        .then(data => {
            if(data.success) refreshFilesList();
        });
    } 
    else if (action === 'ocr') {
        const btn = document.querySelector("button[onclick=\"handleSelected('ocr')\"]");
        const originalText = btn ? btn.innerText : "OCR";
        if(btn) btn.innerText = "Przetwarzanie...";

        fetch('/process_selected', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ files: selectedFiles })
        })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                alert(`Przetworzono ${data.count} plików! Przejdź do zakładki Generowanie, aby użyć danych.`);
                // Opcjonalnie: odśwież listę outputu, jeśli masz taką funkcję
                window.location.reload(); 
            } else {
                alert("Błąd: " + data.error);
            }
        })
        .catch(err => alert("Błąd połączenia: " + err))
        .finally(() => {
            if(btn) btn.innerText = originalText;
        });
    }
}