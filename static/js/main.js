// ==================== OCR ====================
const uploadZone = document.getElementById('uploadZone');
const fileInput = document.getElementById('fileInput');
const fileList = document.getElementById('fileList');
const btnOcr = document.getElementById('btnOcr');
const btnIcon = document.getElementById('btnIcon');
const btnText = document.getElementById('btnText');
const progressBar = document.getElementById('progressBar');
const progressFill = document.getElementById('progressFill');
const statusText = document.getElementById('statusText');
const resultsCard = document.getElementById('resultsCard');
const resultsList = document.getElementById('resultsList');

let selectedFiles = [];

uploadZone.addEventListener('click', () => fileInput.click());

uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('dragover');
});

uploadZone.addEventListener('dragleave', () => {
    uploadZone.classList.remove('dragover');
});

uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('dragover');
    handleFiles(e.dataTransfer.files);
});

fileInput.addEventListener('change', (e) => {
    handleFiles(e.target.files);
});

function handleFiles(files) {
    for (const file of files) {
        if (!selectedFiles.find(f => f.name === file.name)) {
            selectedFiles.push(file);
        }
    }
    renderFileList();
    updateOcrButton();
}

function renderFileList() {
    fileList.innerHTML = selectedFiles.map((file, index) => `
    <div class="file-item">
      <span class="icon">📄</span>
      <span class="name">${file.name}</span>
      <span class="size">${formatSize(file.size)}</span>
      <span class="remove" onclick="removeFile(${index})">✕</span>
    </div>
  `).join('');
}

function removeFile(index) {
    selectedFiles.splice(index, 1);
    renderFileList();
    updateOcrButton();
}

function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function updateOcrButton() {
    btnOcr.disabled = selectedFiles.length === 0;
}

btnOcr.addEventListener('click', async () => {
    if (selectedFiles.length === 0) return;

    btnOcr.disabled = true;
    btnOcr.classList.add('loading');
    btnIcon.innerHTML = '<span class="spinner">⏳</span>';
    btnText.textContent = 'Przetwarzanie...';
    progressBar.classList.remove('hidden');
    statusText.classList.remove('hidden');
    statusText.textContent = 'Ładowanie modelu OCR...';
    progressFill.style.width = '10%';
    resultsCard.classList.add('hidden');

    const formData = new FormData();
    selectedFiles.forEach(file => {
        formData.append('files', file);
    });

    try {
        statusText.textContent = 'Przetwarzanie obrazów...';
        progressFill.style.width = '30%';

        const response = await fetch('/api/process_ocr', {
            method: 'POST',
            body: formData
        });

        progressFill.style.width = '90%';
        const data = await response.json();
        progressFill.style.width = '100%';

        if (data.success) {
            statusText.textContent = `✅ Przetworzono ${data.processed.length} plików`;
            showResults(data);
        } else {
            statusText.textContent = `❌ ${data.error}`;
        }

    } catch (error) {
        statusText.textContent = `❌ ${error.message}`;
    } finally {
        btnOcr.classList.remove('loading');
        btnIcon.textContent = '🚀';
        btnText.textContent = 'Uruchom OCR';
        btnOcr.disabled = false;

        setTimeout(() => {
            progressBar.classList.add('hidden');
        }, 2000);
    }
});

function showResults(data) {
    resultsCard.classList.remove('hidden');

    let html = '';
    data.processed.forEach(filename => {
        html += `
      <div class="result-item">
        <div class="filename">📄 ${filename}</div>
        <div class="status">✓ JSON zapisany w /output</div>
      </div>
    `;
    });

    data.errors.forEach(err => {
        html += `
      <div class="result-item">
        <div class="filename">📄 ${err.file}</div>
        <div class="status error">✕ ${err.error}</div>
      </div>
    `;
    });

    resultsList.innerHTML = html;
    selectedFiles = [];
    renderFileList();
    updateOcrButton();
    loadJsonFiles();
}

// ==================== Templates ====================
const jsonCheckboxList = document.getElementById('jsonCheckboxList');
const refreshJsonList = document.getElementById('refreshJsonList');
const templateSelect = document.getElementById('templateSelect');
const btnTemplate = document.getElementById('btnTemplate');
const btnTemplateIcon = document.getElementById('btnTemplateIcon');
const btnTemplateText = document.getElementById('btnTemplateText');
const templateProgressBar = document.getElementById('templateProgressBar');
const templateProgressFill = document.getElementById('templateProgressFill');
const templateStatusText = document.getElementById('templateStatusText');
const templatePreview = document.getElementById('templatePreview');
const extractedDataCard = document.getElementById('extractedDataCard');
const extractedDataContent = document.getElementById('extractedDataContent');

let currentTemplateFields = [];
let templateIframe = null;

async function loadJsonFiles() {
    try {
        const response = await fetch('/api/ocr_results');
        const files = await response.json();

        if (files.length === 0) {
            jsonCheckboxList.innerHTML = '<div style="color: var(--text-muted); padding: 16px; text-align: center;">Brak plików JSON</div>';
        } else {
            jsonCheckboxList.innerHTML = files.map(file => `
        <div class="checkbox-item">
          <input type="checkbox" id="json_${file}" value="${file}">
          <label for="json_${file}">${file}</label>
        </div>
      `).join('');
        }
        updateTemplateButton();
    } catch (e) {
        console.error('Error loading JSON files:', e);
    }
}

async function loadTemplates() {
    try {
        const response = await fetch('/api/templates');
        const templates = await response.json();

        templateSelect.innerHTML = '<option value="">-- Wybierz szablon --</option>';
        templates.forEach(t => {
            templateSelect.innerHTML += `<option value="${t.filename}">${t.name}</option>`;
        });
    } catch (e) {
        console.error('Error loading templates:', e);
    }
}

loadJsonFiles();
loadTemplates();

refreshJsonList.addEventListener('click', loadJsonFiles);

jsonCheckboxList.addEventListener('change', updateTemplateButton);
templateSelect.addEventListener('change', async () => {
    updateTemplateButton();

    const filename = templateSelect.value;
    if (!filename) {
        templatePreview.innerHTML = '<div style="padding: 48px; text-align: center; color: var(--text-muted);">Wybierz szablon aby zobaczyć podgląd</div>';
        currentTemplateFields = [];
        return;
    }

    try {
        const response = await fetch(`/api/template/${filename}`);
        const data = await response.json();

        currentTemplateFields = data.fields;

        // Create iframe for preview
        templatePreview.innerHTML = '';
        templateIframe = document.createElement('iframe');
        templateIframe.style.width = '100%';
        templateIframe.style.height = '850px';
        templateIframe.style.border = 'none';
        templatePreview.appendChild(templateIframe);

        templateIframe.contentDocument.open();
        templateIframe.contentDocument.write(data.content);

        // Wstrzyknij style paska przewijania
        const style = templateIframe.contentDocument.createElement('style');
        style.textContent = `
            body::-webkit-scrollbar { width: 8px; }
            body::-webkit-scrollbar-track { background: #f1f1f1; }
            body::-webkit-scrollbar-thumb { background: #888; border-radius: 4px; }
            body::-webkit-scrollbar-thumb:hover { background: #555; }
            /* Firefox */
            body { scrollbar-width: thin; scrollbar-color: #888 #f1f1f1; }
        `;
        templateIframe.contentDocument.head.appendChild(style);

        templateIframe.contentDocument.close();

    } catch (e) {
        templatePreview.innerHTML = '<div style="padding: 48px; text-align: center; color: #ff453a;">Błąd ładowania szablonu</div>';
    }
});

function getSelectedJsonFiles() {
    const checkboxes = jsonCheckboxList.querySelectorAll('input[type="checkbox"]:checked');
    return Array.from(checkboxes).map(cb => cb.value);
}

function updateTemplateButton() {
    const selectedFiles = getSelectedJsonFiles();
    const hasTemplate = templateSelect.value !== '';
    btnTemplate.disabled = selectedFiles.length === 0 || !hasTemplate;
}

btnTemplate.addEventListener('click', async () => {
    const selectedFiles = getSelectedJsonFiles();
    const templateFilename = templateSelect.value;

    if (selectedFiles.length === 0 || !templateFilename) return;

    btnTemplate.disabled = true;
    btnTemplate.classList.add('loading');
    btnTemplateIcon.innerHTML = '<span class="spinner">⏳</span>';
    btnTemplateText.textContent = 'Przetwarzanie...';
    templateProgressBar.classList.remove('hidden');
    templateStatusText.classList.remove('hidden');
    templateStatusText.textContent = 'Wysyłanie do AI...';
    templateProgressFill.style.width = '20%';
    extractedDataCard.classList.add('hidden');

    try {
        templateStatusText.textContent = 'Ekstrakcja danych...';
        templateProgressFill.style.width = '50%';

        const response = await fetch('/api/process_template', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                files: selectedFiles,
                fields: currentTemplateFields
            })
        });

        templateProgressFill.style.width = '90%';
        const data = await response.json();
        templateProgressFill.style.width = '100%';

        if (data.success) {
            templateStatusText.textContent = '✅ Ekstrakcja zakończona!';

            // Show extracted data
            extractedDataCard.classList.remove('hidden');
            extractedDataContent.textContent = JSON.stringify(data.fields, null, 2);

            // Fill template inputs
            if (templateIframe && templateIframe.contentDocument) {
                const doc = templateIframe.contentDocument;
                // Pola do pominięcia (uzupełniane automatycznie przez skrypt szablonu)
                const skipFields = ['dokument_miejscowosc_data'];

                for (const [fieldName, value] of Object.entries(data.fields)) {
                    // Pomijaj pola, które są uzupełniane automatycznie
                    if (skipFields.includes(fieldName)) continue;

                    // Znajdź WSZYSTKIE pola o danej nazwie (nie tylko pierwsze)
                    const inputs = doc.querySelectorAll(`input[name="${fieldName}"]`);
                    inputs.forEach(input => {
                        if (input && value) {
                            input.value = value;
                            input.style.background = '#e8f5e9';
                        }
                    });
                }
            }
        } else {
            templateStatusText.textContent = `❌ ${data.error}`;
        }

    } catch (error) {
        templateStatusText.textContent = `❌ ${error.message}`;
    } finally {
        btnTemplate.classList.remove('loading');
        btnTemplateIcon.textContent = '🤖';
        btnTemplateText.textContent = 'Wypełnij szablon AI';
        updateTemplateButton();

        setTimeout(() => {
            templateProgressBar.classList.add('hidden');
        }, 2000);
    }
});

// ==================== TABS ====================
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        // Remove active from all tabs
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

        // Activate clicked tab
        btn.classList.add('active');
        const tabId = btn.dataset.tab;
        document.getElementById('tab-' + tabId).classList.add('active');
    });
});

// ==================== QUICK OCR ====================
const quickUploadZone = document.getElementById('quickUploadZone');
const quickFileInput = document.getElementById('quickFileInput');
const quickFileList = document.getElementById('quickFileList');
const quickTemplateSelect = document.getElementById('quickTemplateSelect');
const btnQuickProcess = document.getElementById('btnQuickProcess');
const btnQuickIcon = document.getElementById('btnQuickIcon');
const btnQuickText = document.getElementById('btnQuickText');
const quickProgressBar = document.getElementById('quickProgressBar');
const quickProgressFill = document.getElementById('quickProgressFill');
const quickStatusText = document.getElementById('quickStatusText');
const quickResultCard = document.getElementById('quickResultCard');
const quickPreview = document.getElementById('quickPreview');

let quickFiles = [];

// Load templates for quick OCR
async function loadQuickTemplates() {
    try {
        const response = await fetch('/api/templates');
        const templates = await response.json();

        quickTemplateSelect.innerHTML = '<option value="">-- Wybierz szablon --</option>';
        templates.forEach(t => {
            quickTemplateSelect.innerHTML += `<option value="${t.filename}">${t.name}</option>`;
        });
    } catch (e) {
        console.error('Error loading templates:', e);
    }
}
loadQuickTemplates();

// Upload zone events
quickUploadZone.addEventListener('click', () => quickFileInput.click());

quickUploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    quickUploadZone.classList.add('dragover');
});

quickUploadZone.addEventListener('dragleave', () => {
    quickUploadZone.classList.remove('dragover');
});

quickUploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    quickUploadZone.classList.remove('dragover');
    handleQuickFiles(e.dataTransfer.files);
});

quickFileInput.addEventListener('change', (e) => {
    handleQuickFiles(e.target.files);
});

function handleQuickFiles(files) {
    for (const file of files) {
        if (!quickFiles.find(f => f.name === file.name)) {
            quickFiles.push(file);
        }
    }
    renderQuickFileList();
    updateQuickButton();
}

function renderQuickFileList() {
    quickFileList.innerHTML = quickFiles.map((file, index) => `
    <div class="file-item">
      <span class="icon">📄</span>
      <span class="name">${file.name}</span>
      <span class="size">${formatSize(file.size)}</span>
      <span class="remove" onclick="removeQuickFile(${index})">✕</span>
    </div>
  `).join('');
}

window.removeQuickFile = function (index) {
    quickFiles.splice(index, 1);
    renderQuickFileList();
    updateQuickButton();
};

function updateQuickButton() {
    btnQuickProcess.disabled = quickFiles.length === 0 || !quickTemplateSelect.value;
}

quickTemplateSelect.addEventListener('change', updateQuickButton);

// Quick Process Button
btnQuickProcess.addEventListener('click', async () => {
    if (quickFiles.length === 0 || !quickTemplateSelect.value) return;

    btnQuickProcess.disabled = true;
    btnQuickProcess.classList.add('loading');
    btnQuickIcon.innerHTML = '<span class="spinner">⏳</span>';
    btnQuickText.textContent = 'Przetwarzanie...';
    quickProgressBar.classList.remove('hidden');
    quickStatusText.classList.remove('hidden');
    quickStatusText.textContent = '📷 Ładowanie modelu OCR...';
    quickProgressFill.style.width = '10%';
    quickResultCard.classList.add('hidden');

    const formData = new FormData();
    quickFiles.forEach(file => {
        formData.append('files', file);
    });
    formData.append('template', quickTemplateSelect.value);

    try {
        quickStatusText.textContent = '📷 Przetwarzanie OCR...';
        quickProgressFill.style.width = '30%';

        const response = await fetch('/api/quick_process', {
            method: 'POST',
            body: formData
        });

        quickStatusText.textContent = '🤖 Ekstrakcja danych przez AI...';
        quickProgressFill.style.width = '70%';

        const data = await response.json();
        quickProgressFill.style.width = '100%';

        if (data.success) {
            quickStatusText.textContent = '✅ Zakończono! Ładowanie szablonu...';

            // Load template and fill with data
            const templateResponse = await fetch(`/api/template/${data.template}`);
            const templateData = await templateResponse.json();

            // Create iframe with filled template
            quickResultCard.classList.remove('hidden');
            quickPreview.innerHTML = '';

            const iframe = document.createElement('iframe');
            iframe.style.width = '100%';
            iframe.style.height = '500px';
            iframe.style.border = 'none';
            quickPreview.appendChild(iframe);

            iframe.contentDocument.open();
            iframe.contentDocument.write(templateData.content);

            // Wstrzyknij style paska przewijania
            const style = iframe.contentDocument.createElement('style');
            style.textContent = `
                body::-webkit-scrollbar { width: 8px; }
                body::-webkit-scrollbar-track { background: #f1f1f1; }
                body::-webkit-scrollbar-thumb { background: #888; border-radius: 4px; }
                body::-webkit-scrollbar-thumb:hover { background: #555; }
                /* Firefox */
                body { scrollbar-width: thin; scrollbar-color: #888 #f1f1f1; }
            `;
            iframe.contentDocument.head.appendChild(style);

            iframe.contentDocument.close();

            // Fill inputs
            setTimeout(() => {
                const doc = iframe.contentDocument;
                // Pola do pominięcia (uzupełniane automatycznie przez skrypt szablonu)
                const skipFields = ['dokument_miejscowosc_data'];

                for (const [fieldName, value] of Object.entries(data.fields)) {
                    // Pomijaj pola, które są uzupełniane automatycznie
                    if (skipFields.includes(fieldName)) continue;

                    // Znajdź WSZYSTKIE pola o danej nazwie (nie tylko pierwsze)
                    const inputs = doc.querySelectorAll(`input[name="${fieldName}"]`);
                    inputs.forEach(input => {
                        if (input && value) {
                            input.value = value;
                            input.style.background = '#e8f5e9';
                        }
                    });
                }
            }, 100);

            // Clear files
            quickFiles = [];
            renderQuickFileList();

        } else {
            quickStatusText.textContent = `❌ ${data.error}`;
        }

    } catch (error) {
        quickStatusText.textContent = `❌ ${error.message}`;
    } finally {
        btnQuickProcess.classList.remove('loading');
        btnQuickIcon.textContent = '🚀';
        btnQuickText.textContent = 'Przetwórz i wypełnij';
        updateQuickButton();

        setTimeout(() => {
            quickProgressBar.classList.add('hidden');
        }, 2000);
    }
});

// ==================== PRINT TO PDF ====================
const btnPrintPdf = document.getElementById('btnPrintPdf');

btnPrintPdf.addEventListener('click', () => {
    // Znajdź iframe z wypełnionym szablonem
    const iframe = quickPreview.querySelector('iframe');

    if (!iframe || !iframe.contentWindow) {
        alert('Brak dokumentu do wydrukowania!');
        return;
    }

    // Drukuj zawartość iframe
    iframe.contentWindow.focus();
    iframe.contentWindow.print();
});
