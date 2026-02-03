// ==================== HELPER FUNCTIONS ====================
// Przesuwa datę o jeden dzień (format: DD.MM.YYYY)
function addOneDay(dateStr) {
    if (!dateStr || typeof dateStr !== 'string') return dateStr;

    const parts = dateStr.split('.');
    if (parts.length !== 3) return dateStr;

    const day = parseInt(parts[0], 10);
    const month = parseInt(parts[1], 10) - 1; // JS months are 0-indexed
    const year = parseInt(parts[2], 10);

    if (isNaN(day) || isNaN(month) || isNaN(year)) return dateStr;

    const date = new Date(year, month, day);
    date.setDate(date.getDate() + 1);

    const newDay = String(date.getDate()).padStart(2, '0');
    const newMonth = String(date.getMonth() + 1).padStart(2, '0');
    const newYear = date.getFullYear();

    return `${newDay}.${newMonth}.${newYear}`;
}

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

if (uploadZone) {
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
}

if (fileInput) {
    fileInput.addEventListener('change', (e) => handleFiles(e.target.files));
}


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
    if (!fileList) return;
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
    if (!btnOcr) return;
    btnOcr.disabled = selectedFiles.length === 0;
}

if (btnOcr) {
    btnOcr.addEventListener('click', async () => {
        if (selectedFiles.length === 0) return;

        btnOcr.disabled = true;
        btnOcr.classList.add('loading');
        if (btnIcon) btnIcon.innerHTML = '<span class="spinner">⏳</span>';
        if (btnText) btnText.textContent = 'Przetwarzanie...';
        if (progressBar) progressBar.classList.remove('hidden');
        if (statusText) {
            statusText.classList.remove('hidden');
            statusText.textContent = 'Ładowanie modelu OCR...';
        }
        if (progressFill) progressFill.style.width = '10%';
        if (resultsCard) resultsCard.classList.add('hidden');

        const formData = new FormData();

        selectedFiles.forEach(file => {
            formData.append('files', file);
        });

        try {
            if (statusText) statusText.textContent = 'Przetwarzanie obrazów...';
            if (progressFill) progressFill.style.width = '30%';

            const response = await fetch('/api/process_ocr', {
                method: 'POST',
                body: formData
            });

            if (progressFill) progressFill.style.width = '90%';
            const data = await response.json();
            if (progressFill) progressFill.style.width = '100%';

            if (data.success) {
                if (statusText) statusText.textContent = `✅ Przetworzono ${data.processed.length} plików`;
                showResults(data);
            } else {
                if (statusText) statusText.textContent = `❌ ${data.error}`;
            }

        } catch (error) {
            if (statusText) statusText.textContent = `❌ ${error.message}`;
        } finally {
            btnOcr.classList.remove('loading');
            if (btnIcon) btnIcon.textContent = '🚀';
            if (btnText) btnText.textContent = 'Uruchom OCR';
            btnOcr.disabled = false;

            setTimeout(() => {
                if (progressBar) progressBar.classList.add('hidden');
            }, 2000);
        }
    });
}

function showResults(data) {
    if (!resultsCard || !resultsList) return;
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

// ==================== Templates - ADVANCED MODE ====================
const templateSelect = document.getElementById('templateSelect');
const templatePreview = document.getElementById('templatePreview');
const extractedDataCard = document.getElementById('extractedDataCard');
const extractedDataContent = document.getElementById('extractedDataContent');
const advSaveWezwanieSection = document.getElementById('advSaveWezwanieSection');
const advBtnSaveWezwanie = document.getElementById('advBtnSaveWezwanie');

// Kroki workflow
const advStepSource = document.getElementById('advStepSource');
const advStepSourcePozew = document.getElementById('advStepSourcePozew');
const advStepLlm = document.getElementById('advStepLlm');
const advStepPozewExtra = document.getElementById('advStepPozewExtra');
const advDividerStep2 = document.getElementById('advDividerStep2');
const advDividerStep3 = document.getElementById('advDividerStep3');
const advWezwaniaList = document.getElementById('advWezwaniaList');
const advRefreshWezwaniaList = document.getElementById('advRefreshWezwaniaList');

// Źródło danych - OCR vs JSON
const btnSourceOcr = document.getElementById('btnSourceOcr');
const btnSourceJson = document.getElementById('btnSourceJson');
const ocrSection = document.getElementById('ocrSection');
const jsonSection = document.getElementById('jsonSection');
const jsonCheckboxList = document.getElementById('jsonCheckboxList');
const refreshJsonList = document.getElementById('refreshJsonList');

// OCR elementy
const advUploadZone = document.getElementById('advUploadZone');
const advFileInput = document.getElementById('advFileInput');
const advFileList = document.getElementById('advFileList');
const btnRunOcr = document.getElementById('btnRunOcr');
const btnOcrIcon = document.getElementById('btnOcrIcon');
const btnOcrText = document.getElementById('btnOcrText');
const ocrProgressBar = document.getElementById('ocrProgressBar');
const ocrProgressFill = document.getElementById('ocrProgressFill');
const ocrStatusText = document.getElementById('ocrStatusText');

// LLM elementy
const btnRunLlm = document.getElementById('btnRunLlm');
const btnLlmIcon = document.getElementById('btnLlmIcon');
const btnLlmText = document.getElementById('btnLlmText');
const llmProgressBar = document.getElementById('llmProgressBar');
const llmProgressFill = document.getElementById('llmProgressFill');
const llmStatusText = document.getElementById('llmStatusText');
const selectedJsonInfo = document.getElementById('selectedJsonInfo');

let currentTemplateFields = [];
let templateIframe = null;
let advWorkflowType = null; // 'wezwanie' or 'pozew'
let advUploadedFiles = [];
let advDataSource = 'ocr'; // 'ocr' or 'json'

async function loadTemplates() {
    if (!templateSelect) return;
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

async function loadJsonFiles() {
    if (!jsonCheckboxList) return;
    try {
        const response = await fetch('/api/ocr_results');
        const files = await response.json();

        if (files.length === 0) {
            jsonCheckboxList.innerHTML = '<div style="color: var(--text-muted); padding: 16px; text-align: center;">Brak plików JSON. Najpierw uruchom OCR.</div>';
        } else {
            jsonCheckboxList.innerHTML = files.map(file => `
                <div class="checkbox-item">
                    <input type="checkbox" id="json_${file}" value="${file}" onchange="updateLlmButton()">
                    <label for="json_${file}">${file}</label>
                </div>
            `).join('');
        }
        updateLlmButton();
    } catch (e) {
        console.error('Error loading JSON files:', e);
    }
}

// Zmienna do przechowywania wybranych wezwań w trybie zaawansowanym
let selectedAdvWezwania = [];

// Funkcja ładowania listy wezwań dla pozwu w trybie zaawansowanym
async function loadAdvWezwaniaList() {
    if (!advWezwaniaList) return;
    try {
        const response = await fetch('/api/wezwania');
        const wezwania = await response.json();

        if (wezwania.length === 0) {
            advWezwaniaList.innerHTML = `
                <div style="color: var(--text-muted); padding: 16px; text-align: center;">
                    Brak zapisanych wezwań. Najpierw wygeneruj Wezwanie do Zapłaty.
                </div>`;
        } else {
            advWezwaniaList.innerHTML = wezwania.map(w => `
                <div class="checkbox-item">
                    <input type="checkbox" id="advWez_${w.id}" value="${w.id}" 
                        onchange="toggleAdvWezwanieSelection('${w.id}')">
                    <label for="advWez_${w.id}">
                        <strong>${w.dluznik_nazwa}</strong><br>
                        <span style="font-size: 0.85em; color: #666;">
                            Faktura: ${w.faktura_numer} | ${w.kwota} | ${new Date(w.created_at).toLocaleDateString('pl-PL')}
                        </span>
                    </label>
                </div>
            `).join('');
        }
    } catch (e) {
        console.error('Error loading wezwania:', e);
        advWezwaniaList.innerHTML = '<div style="color: red; padding: 16px;">Błąd ładowania wezwań</div>';
    }
}

// Obsługa wyboru wezwań w trybie zaawansowanym
window.toggleAdvWezwanieSelection = function (id) {
    const index = selectedAdvWezwania.indexOf(id);
    if (index > -1) {
        selectedAdvWezwania.splice(index, 1);
    } else {
        selectedAdvWezwania.push(id);
    }
};

// Przycisk odświeżania listy wezwań
if (advRefreshWezwaniaList) {
    advRefreshWezwaniaList.addEventListener('click', loadAdvWezwaniaList);
}

loadTemplates();

// === PRZEŁĄCZANIE ŹRÓDŁA (OCR vs JSON) ===
if (btnSourceOcr) {
    btnSourceOcr.addEventListener('click', () => {
        advDataSource = 'ocr';
        btnSourceOcr.classList.add('active');
        btnSourceJson.classList.remove('active');
        ocrSection.classList.remove('hidden');
        jsonSection.classList.add('hidden');
        updateLlmButton();
    });
}

if (btnSourceJson) {
    btnSourceJson.addEventListener('click', () => {
        advDataSource = 'json';
        btnSourceJson.classList.add('active');
        btnSourceOcr.classList.remove('active');
        jsonSection.classList.remove('hidden');
        ocrSection.classList.add('hidden');
        loadJsonFiles();
        updateLlmButton();
    });
}

if (refreshJsonList) {
    refreshJsonList.addEventListener('click', loadJsonFiles);
}

// === UPLOAD ZONE DLA OCR ===
if (advUploadZone) {
    advUploadZone.addEventListener('click', () => advFileInput.click());

    advUploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        advUploadZone.classList.add('dragover');
    });

    advUploadZone.addEventListener('dragleave', () => {
        advUploadZone.classList.remove('dragover');
    });

    advUploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        advUploadZone.classList.remove('dragover');
        handleAdvUploadFiles(e.dataTransfer.files);
    });
}

if (advFileInput) {
    advFileInput.addEventListener('change', (e) => {
        handleAdvUploadFiles(e.target.files);
    });
}

function handleAdvUploadFiles(files) {
    for (const file of files) {
        if (!advUploadedFiles.find(f => f.name === file.name)) {
            advUploadedFiles.push(file);
        }
    }
    renderAdvFileList();
    updateOcrButton();
}

function renderAdvFileList() {
    if (!advFileList) return;
    advFileList.innerHTML = advUploadedFiles.map((file, index) => `
        <div class="file-item">
            <span class="icon">📄</span>
            <span class="name">${file.name}</span>
            <span class="size">${formatSize(file.size)}</span>
            <span class="remove" onclick="removeAdvFile(${index})">✕</span>
        </div>
    `).join('');
}

window.removeAdvFile = function (index) {
    advUploadedFiles.splice(index, 1);
    renderAdvFileList();
    updateOcrButton();
};

function updateOcrButton() {
    const btnOcrFill = document.getElementById('btnOcrFill');
    if (btnOcrFill) {
        btnOcrFill.disabled = advUploadedFiles.length === 0;
    }
}

// === OCR + FILL PROCESSING ===
const btnOcrFill = document.getElementById('btnOcrFill');
if (btnOcrFill) {
    btnOcrFill.addEventListener('click', async () => {
        if (advUploadedFiles.length === 0) return;

        const btnOcrFillIcon = document.getElementById('btnOcrFillIcon');
        const btnOcrFillText = document.getElementById('btnOcrFillText');
        const ocrFillProgressBar = document.getElementById('ocrFillProgressBar');
        const ocrFillProgressFill = document.getElementById('ocrFillProgressFill');
        const ocrFillStatusText = document.getElementById('ocrFillStatusText');

        btnOcrFill.disabled = true;
        btnOcrFill.classList.add('loading');
        if (btnOcrFillIcon) btnOcrFillIcon.innerHTML = '<span class="spinner">⏳</span>';
        if (btnOcrFillText) btnOcrFillText.textContent = 'Przetwarzanie...';
        if (ocrFillProgressBar) ocrFillProgressBar.classList.remove('hidden');
        if (ocrFillStatusText) {
            ocrFillStatusText.classList.remove('hidden');
            ocrFillStatusText.textContent = `📷 Przetwarzanie ${advUploadedFiles.length} dokumentów...`;
        }
        if (ocrFillProgressFill) ocrFillProgressFill.style.width = '10%';

        const formData = new FormData();
        advUploadedFiles.forEach(file => formData.append('files', file));

        const templateName = templateSelect ? templateSelect.value : '';
        if (templateName) formData.append('template', templateName);

        try {
            if (ocrFillStatusText) ocrFillStatusText.textContent = '🤖 OCR + Analiza AI...';
            if (ocrFillProgressFill) ocrFillProgressFill.style.width = '30%';

            const response = await fetch('/api/process_ocr', {
                method: 'POST',
                body: formData
            });

            if (ocrFillProgressFill) ocrFillProgressFill.style.width = '80%';
            const data = await response.json();

            if (data.success && data.documents && data.documents.length > 0) {
                if (ocrFillStatusText) ocrFillStatusText.textContent = `✅ Przetworzono ${data.documents.length} dokumentów!`;
                if (ocrFillProgressFill) ocrFillProgressFill.style.width = '100%';

                // Agreguj dane z wielu dokumentów
                const invoiceNumbers = [];
                const invoiceDates = [];
                let totalAmount = 0;
                let latestPaymentDate = null;
                let latestPaymentDateStr = '';
                const mergedFields = {};

                // Pola kwoty i numeru faktury
                const amountFieldPattern = /kwot/i;
                const invoiceNumPattern = /numer_faktury/i;
                const paymentDatePattern = /terminu_platnosci|date_terminu/i;
                const invoiceDatePattern = /date_wystawienia/i;

                data.documents.forEach(doc => {
                    const fields = doc.fields || {};

                    for (let [key, value] of Object.entries(fields)) {
                        if (!value) continue;

                        // Zbierz numery faktur
                        if (invoiceNumPattern.test(key)) {
                            if (!invoiceNumbers.includes(value)) {
                                invoiceNumbers.push(value);
                            }
                        }
                        // Zbierz kwoty i sumuj
                        else if (amountFieldPattern.test(key)) {
                            const numStr = String(value).replace(/[^\d,.]/g, '').replace(',', '.');
                            const num = parseFloat(numStr);
                            if (!isNaN(num)) totalAmount += num;
                        }
                        // Zbierz daty wystawienia
                        else if (invoiceDatePattern.test(key)) {
                            if (!invoiceDates.includes(value)) {
                                invoiceDates.push(value);
                            }
                        }
                        // Znajdź najpóźniejszy termin płatności
                        else if (paymentDatePattern.test(key)) {
                            const parsed = parsePolishDate(value);
                            if (parsed && (!latestPaymentDate || parsed > latestPaymentDate)) {
                                latestPaymentDate = parsed;
                                latestPaymentDateStr = value;
                            }
                        }
                        // Inne pola - weź z pierwszego dokumentu
                        else if (!mergedFields[key]) {
                            mergedFields[key] = value;
                        }
                    }
                });

                // Wypełnij szablon
                if (templateIframe && templateIframe.contentDocument) {
                    const doc = templateIframe.contentDocument;

                    // Wypełnij pozostałe pola z pierwszego dokumentu
                    for (let [fieldName, value] of Object.entries(mergedFields)) {
                        if (!value) continue;
                        const inputs = doc.querySelectorAll(`input[name="${fieldName}"]`);
                        inputs.forEach(input => {
                            input.value = value;
                            input.style.background = '#e8f5e9';
                        });
                    }

                    // Wstaw połączone numery faktur
                    const invoiceInputs = doc.querySelectorAll('input[name*="numer_faktury"]');
                    invoiceInputs.forEach(input => {
                        input.value = invoiceNumbers.join(', ');
                        input.style.background = '#e3f2fd';
                    });

                    // Wstaw połączone daty wystawienia
                    const dateInputs = doc.querySelectorAll('input[name*="date_wystawienia"]');
                    dateInputs.forEach(input => {
                        input.value = invoiceDates.join(', ');
                        input.style.background = '#e8f5e9';
                    });

                    // Wstaw sumę kwot
                    const amountInputs = doc.querySelectorAll('input[name*="kwot"]');
                    amountInputs.forEach(input => {
                        input.value = totalAmount.toFixed(2) + ' zł';
                        input.style.background = '#fff3e0';
                    });

                    // Wstaw termin płatności +1 dzień (odsetki od następnego dnia)
                    if (latestPaymentDateStr) {
                        const nextDay = addOneDay(latestPaymentDateStr);
                        const paymentInputs = doc.querySelectorAll('input[name*="terminu_platnosci"], input[name*="date_terminu"]');
                        paymentInputs.forEach(input => {
                            input.value = nextDay;
                            input.style.background = '#fce4ec';
                        });
                    }

                    // Pokaż sekcję zapisywania dla wezwania
                    if (advWorkflowType === 'wezwanie' && advSaveWezwanieSection) {
                        advSaveWezwanieSection.classList.remove('hidden');
                    }
                }

                // Pokaż wyekstrahowane dane
                if (extractedDataCard && extractedDataContent) {
                    extractedDataCard.classList.remove('hidden');
                    extractedDataContent.textContent = JSON.stringify({
                        dokumenty: data.documents.length,
                        numery_faktur: invoiceNumbers,
                        suma_kwot: totalAmount.toFixed(2) + ' zł',
                        termin_odsetek: latestPaymentDateStr ? addOneDay(latestPaymentDateStr) : null,
                        wszystkie_dane: data.documents
                    }, null, 2);
                }

                // Wyczyść pliki
                advUploadedFiles = [];
                renderAdvFileList();

            } else if (data.success) {
                if (ocrFillStatusText) ocrFillStatusText.textContent = '⚠️ Brak danych do ekstrakcji';
            } else {
                if (ocrFillStatusText) ocrFillStatusText.textContent = `❌ ${data.error}`;
            }

        } catch (error) {
            if (ocrFillStatusText) ocrFillStatusText.textContent = `❌ ${error.message}`;
        } finally {
            btnOcrFill.classList.remove('loading');
            if (btnOcrFillIcon) btnOcrFillIcon.textContent = '🚀';
            if (btnOcrFillText) btnOcrFillText.textContent = 'OCR + Uzupełnij szablon';
            updateOcrButton();

            setTimeout(() => {
                if (ocrFillProgressBar) ocrFillProgressBar.classList.add('hidden');
            }, 3000);
        }
    });
}

// Funkcja do parsowania polskiej daty DD.MM.YYYY
function parsePolishDate(dateStr) {
    if (!dateStr) return null;
    const clean = String(dateStr).replace(/r\.?$/i, '').trim();
    const parts = clean.split('.');
    if (parts.length === 3) {
        const d = parseInt(parts[0], 10);
        const m = parseInt(parts[1], 10) - 1;
        const y = parseInt(parts[2], 10);
        if (!isNaN(d) && !isNaN(m) && !isNaN(y)) {
            return new Date(y, m, d);
        }
    }
    return null;
}

// === LLM PROCESSING ===
if (btnRunLlm) {
    btnRunLlm.addEventListener('click', async () => {
        const selectedFiles = getSelectedJsonFiles();
        if (selectedFiles.length === 0) return;

        btnRunLlm.disabled = true;
        btnRunLlm.classList.add('loading');
        if (btnLlmIcon) btnLlmIcon.innerHTML = '<span class="spinner">⏳</span>';
        if (btnLlmText) btnLlmText.textContent = 'Przetwarzanie...';
        if (llmProgressBar) llmProgressBar.classList.remove('hidden');
        if (llmStatusText) {
            llmStatusText.classList.remove('hidden');
            llmStatusText.textContent = '🤖 Wysyłanie do AI...';
        }
        if (llmProgressFill) llmProgressFill.style.width = '20%';
        if (extractedDataCard) extractedDataCard.classList.add('hidden');

        try {
            // Dla wielu plików w wezwaniu - przetwarzaj każdy osobno
            const isMultipleInvoices = selectedFiles.length > 1 && advWorkflowType === 'wezwanie';
            const endpoint = isMultipleInvoices ? '/api/process_multiple_invoices' : '/api/process_template';

            if (isMultipleInvoices) {
                if (llmStatusText) llmStatusText.textContent = `🤖 Przetwarzanie ${selectedFiles.length} faktur osobno...`;
            } else {
                if (llmStatusText) llmStatusText.textContent = '🤖 Ekstrakcja danych...';
            }
            if (llmProgressFill) llmProgressFill.style.width = '50%';

            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    files: selectedFiles,
                    fields: currentTemplateFields
                })
            });

            if (llmProgressFill) llmProgressFill.style.width = '90%';
            const data = await response.json();
            if (llmProgressFill) llmProgressFill.style.width = '100%';

            if (data.success) {
                if (isMultipleInvoices) {
                    // Obsługa wielu faktur
                    if (llmStatusText) llmStatusText.textContent = `✅ Przetworzono ${data.invoices?.length || 0} faktur! Zapisano do: ${data.output_folder}`;

                    if (extractedDataCard) extractedDataCard.classList.remove('hidden');
                    if (extractedDataContent) {
                        extractedDataContent.textContent = JSON.stringify({
                            invoices: data.invoices,
                            total_amount: data.total_amount,
                            common_data: data.common_data
                        }, null, 2);
                    }

                    // Wypełnij szablon danymi wspólnymi + pierwszą fakturą
                    if (templateIframe && templateIframe.contentDocument) {
                        const doc = templateIframe.contentDocument;
                        const skipFields = ['Wpisz_aktualne_miasto_uzytkownika_oraz_dzisiejsza_date_w_formacie_Miejscowosc_Data'];

                        // Wypełnij wspólne dane (wierzyciel, dłużnik)
                        for (let [fieldName, value] of Object.entries(data.common_data || {})) {
                            if (skipFields.includes(fieldName) || !value) continue;
                            const inputs = doc.querySelectorAll(`input[name="${fieldName}"]`);
                            inputs.forEach(input => {
                                input.value = value;
                                input.style.background = '#e8f5e9';
                            });
                        }

                        // Wypełnij dane z faktur
                        if (data.invoices && data.invoices.length > 0) {
                            // Połącz numery wszystkich faktur i wstaw do WSZYSTKICH pól numeru
                            const allNumers = data.invoices.map(i => i.numer).filter(n => n).join(', ');
                            const numerInputs = doc.querySelectorAll('input[name="Znajdz_i_przepisz_numer_faktury_ktorej_dotyczy_to_wezwanie_do_zaplaty"]');
                            numerInputs.forEach(input => {
                                input.value = allNumers;
                                input.style.background = '#e8f5e9';
                            });

                            // Połącz daty wystawienia wszystkich faktur po przecinku
                            const allDates = data.invoices.map(i => i.data).filter(d => d).join(', ');

                            // Funkcja do parsowania daty w formacie DD.MM.YYYY
                            function parsePolishDate(dateStr) {
                                if (!dateStr) return null;
                                const parts = dateStr.replace(/r\.?$/i, '').trim().split('.');
                                if (parts.length === 3) {
                                    const d = parseInt(parts[0], 10);
                                    const m = parseInt(parts[1], 10) - 1;
                                    const y = parseInt(parts[2], 10);
                                    if (!isNaN(d) && !isNaN(m) && !isNaN(y)) {
                                        return new Date(y, m, d);
                                    }
                                }
                                return null;
                            }

                            // Znajdź najpóźniejszy termin płatności (od niego liczymy odsetki)
                            let latestTerminDate = null;
                            let latestTerminStr = '';
                            data.invoices.forEach(inv => {
                                const parsed = parsePolishDate(inv.termin);
                                if (parsed && (!latestTerminDate || parsed > latestTerminDate)) {
                                    latestTerminDate = parsed;
                                    latestTerminStr = inv.termin;
                                }
                            });

                            const dataInput = doc.querySelector('input[name="Znajdz_na_fakturze_date_wystawienia_dokumentu_lub_date_sprzedazy"]');
                            const terminInput = doc.querySelector('input[name="Znajdz_na_fakturze_date_terminu_platnosci_od_ktorej_beda_liczone_odsetki"]');

                            if (dataInput && allDates) {
                                dataInput.value = allDates;
                                dataInput.style.background = '#e8f5e9';
                            }
                            if (terminInput && latestTerminStr) {
                                terminInput.value = addOneDay(latestTerminStr);
                                terminInput.style.background = '#e8f5e9';
                            }
                        }

                        // Wstaw łączną kwotę
                        const kwotaInput = doc.querySelector('input[name="Znajdz_na_fakturze_koncowa_kwote_do_zaplaty_opisana_czesto_jako_Razem_lub_Do_zaplaty_brutto_wraz_z_waluta"]');
                        if (kwotaInput && data.total_amount) {
                            kwotaInput.value = data.total_amount + ' zł';
                            kwotaInput.style.background = '#fff3e0';
                        }
                    }

                } else {
                    // Standardowa obsługa
                    if (llmStatusText) llmStatusText.textContent = '✅ Ekstrakcja zakończona!';

                    if (extractedDataCard) extractedDataCard.classList.remove('hidden');
                    if (extractedDataContent) extractedDataContent.textContent = JSON.stringify(data.fields, null, 2);

                    // Fill template
                    if (templateIframe && templateIframe.contentDocument) {
                        const doc = templateIframe.contentDocument;
                        const skipFields = ['Wpisz_aktualne_miasto_uzytkownika_oraz_dzisiejsza_date_w_formacie_Miejscowosc_Data'];

                        // Funkcja do elastycznego znajdowania inputa - obsługuje warianty nazw od LLM
                        function findMatchingInputs(doc, fieldName) {
                            // Najpierw spróbuj dokładnego dopasowania
                            let inputs = doc.querySelectorAll(`input[name="${fieldName}"]`);
                            if (inputs.length > 0) return inputs;

                            // Jeśli nie znaleziono, szukaj podobnych nazw
                            const allInputs = doc.querySelectorAll('input[name]');
                            const matchingInputs = [];

                            // Warianty do próby: zamień końcówki gramatyczne
                            const variants = [
                                fieldName,
                                fieldName.replace('wezwania', 'wezwanie'),
                                fieldName.replace('wezwanie', 'wezwania'),
                                fieldName.replace('kwote', 'kwota'),
                                fieldName.replace('kwota', 'kwote'),
                                fieldName.replace('nazwe', 'nazwa'),
                                fieldName.replace('nazwa', 'nazwe')
                            ];

                            allInputs.forEach(input => {
                                const inputName = input.getAttribute('name');
                                if (variants.includes(inputName)) {
                                    matchingInputs.push(input);
                                }
                            });

                            return matchingInputs;
                        }

                        for (let [fieldName, value] of Object.entries(data.fields)) {
                            if (skipFields.includes(fieldName) || !value) continue;

                            // Dla terminu płatności - przesuń datę o 1 dzień
                            if (fieldName.includes('terminu_platnosci') || fieldName.includes('date_terminu')) {
                                value = addOneDay(value);
                            }

                            const inputs = findMatchingInputs(doc, fieldName);
                            inputs.forEach(input => {
                                input.value = value;
                                input.style.background = '#e8f5e9';
                            });
                        }
                    }
                }

                // Show save button only for wezwanie
                if (advWorkflowType === 'wezwanie' && advSaveWezwanieSection) {
                    advSaveWezwanieSection.classList.remove('hidden');
                }

            } else {
                if (llmStatusText) llmStatusText.textContent = `❌ ${data.error}`;
            }

        } catch (error) {
            if (llmStatusText) llmStatusText.textContent = `❌ ${error.message}`;
        } finally {
            btnRunLlm.classList.remove('loading');
            if (btnLlmIcon) btnLlmIcon.textContent = '🤖';
            if (btnLlmText) btnLlmText.textContent = 'Wypełnij szablon AI';
            updateLlmButton();

            setTimeout(() => {
                if (llmProgressBar) llmProgressBar.classList.add('hidden');
            }, 2000);
        }
    });
}



// === TEMPLATE SELECTION - WORKFLOW BRANCHING ===

if (templateSelect) {
    templateSelect.addEventListener('change', async function () {
        const filename = this.value;

        // Hide all step sections
        if (advStepSource) advStepSource.classList.add('hidden');
        if (advStepSourcePozew) advStepSourcePozew.classList.add('hidden');
        if (advStepLlm) advStepLlm.classList.add('hidden');
        if (advStepPozewExtra) advStepPozewExtra.classList.add('hidden');
        if (advDividerStep2) advDividerStep2.classList.add('hidden');
        if (advDividerStep3) advDividerStep3.classList.add('hidden');
        if (advSaveWezwanieSection) advSaveWezwanieSection.classList.add('hidden');

        if (!filename) {
            advWorkflowType = null;
            if (templatePreview) templatePreview.innerHTML = '<div style="padding: 48px; text-align: center; color: var(--text-muted);">Wybierz szablon aby zobaczyć podgląd</div>';
            currentTemplateFields = [];
            return;
        }

        // Show workflow sections based on template type
        if (advDividerStep2) advDividerStep2.classList.remove('hidden');

        if (filename.includes('wezwanie')) {
            advWorkflowType = 'wezwanie';
            // Dla wezwania - pokaż sekcję upload
            const advStepUpload = document.getElementById('advStepUpload');
            if (advStepUpload) advStepUpload.classList.remove('hidden');
        } else if (filename.includes('pozew')) {
            advWorkflowType = 'pozew';
            // Dla pozwu - pokaż sekcję z wezwaniami
            if (advStepSourcePozew) advStepSourcePozew.classList.remove('hidden');
            if (advStepPozewExtra) advStepPozewExtra.classList.remove('hidden');
            // Załaduj listę wezwań
            loadAdvWezwaniaList();
        }


        // Load template preview
        try {
            const response = await fetch(`/api/template/${filename}`);
            const data = await response.json();

            currentTemplateFields = data.fields;

            if (templatePreview) {
                templatePreview.innerHTML = '';
                templateIframe = document.createElement('iframe');
                templateIframe.style.width = '100%';
                templateIframe.style.height = '850px';
                templateIframe.style.border = 'none';
                templateIframe.id = 'advDocumentIframe';
                templatePreview.appendChild(templateIframe);

                templateIframe.contentDocument.open();
                templateIframe.contentDocument.write(data.content);

                const style = templateIframe.contentDocument.createElement('style');
                style.textContent = `
                    body::-webkit-scrollbar { width: 8px; }
                    body::-webkit-scrollbar-track { background: #f1f1f1; }
                    body::-webkit-scrollbar-thumb { background: #888; border-radius: 4px; }
                    body::-webkit-scrollbar-thumb:hover { background: #555; }
                    body { scrollbar-width: thin; scrollbar-color: #888 #f1f1f1; }
                `;
                templateIframe.contentDocument.head.appendChild(style);
                templateIframe.contentDocument.close();
            }

            const btnPrint = document.getElementById('btnPrintTemplate');
            if (btnPrint) {
                btnPrint.disabled = false;
                btnPrint.onclick = function () {
                    if (templateIframe && templateIframe.contentWindow) {
                        templateIframe.contentWindow.focus();
                        templateIframe.contentWindow.print();
                    }
                };
            }

        } catch (e) {
            if (templatePreview) templatePreview.innerHTML = '<div style="padding: 48px; text-align: center; color: #ff453a;">Błąd ładowania szablonu</div>';
        }
    });
}

// === SAVE WEZWANIE (ADVANCED) ===
if (advBtnSaveWezwanie) {
    advBtnSaveWezwanie.addEventListener('click', async () => {

        const iframe = document.getElementById('advDocumentIframe');
        if (!iframe) {
            alert('Brak dokumentu do zapisania!');
            return;
        }

        const doc = iframe.contentDocument;
        const fields = {};

        doc.querySelectorAll('input[name]').forEach(input => {
            fields[input.name] = input.value;
        });

        try {
            const response = await fetch('/api/wezwania/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ fields })
            });

            const result = await response.json();

            if (result.success) {
                alert(`✅ Wezwanie zapisane!\nID: ${result.id}`);
                advSaveWezwanieSection.innerHTML = `
                    <p style="margin: 0; color: #2e7d32; font-weight: 500;">
                        ✅ Wezwanie zapisane (ID: ${result.id})
                    </p>`;
            } else {
                alert(`❌ Błąd: ${result.error}`);
            }
        } catch (e) {
            alert(`❌ Błąd zapisu: ${e.message}`);
        }
    });
}

// === POZEW SOURCE TOGGLE ===
const btnPozewSourceSaved = document.getElementById('btnPozewSourceSaved');
const btnPozewSourceUpload = document.getElementById('btnPozewSourceUpload');
const pozewSavedSection = document.getElementById('pozewSavedSection');
const pozewUploadSection = document.getElementById('pozewUploadSection');
const pozewUploadZone = document.getElementById('pozewUploadZone');
const pozewFileInput = document.getElementById('pozewFileInput');
const pozewFileList = document.getElementById('pozewFileList');
const btnPozewOcr = document.getElementById('btnPozewOcr');

let pozewUploadedFiles = [];

if (btnPozewSourceSaved) {
    btnPozewSourceSaved.addEventListener('click', () => {
        btnPozewSourceSaved.classList.add('active');
        btnPozewSourceUpload.classList.remove('active');
        if (pozewSavedSection) pozewSavedSection.classList.remove('hidden');
        if (pozewUploadSection) pozewUploadSection.classList.add('hidden');
    });
}

if (btnPozewSourceUpload) {
    btnPozewSourceUpload.addEventListener('click', () => {
        btnPozewSourceUpload.classList.add('active');
        btnPozewSourceSaved.classList.remove('active');
        if (pozewUploadSection) pozewUploadSection.classList.remove('hidden');
        if (pozewSavedSection) pozewSavedSection.classList.add('hidden');
    });
}

// Pozew upload zone
if (pozewUploadZone) {
    pozewUploadZone.addEventListener('click', () => pozewFileInput?.click());
    pozewUploadZone.addEventListener('dragover', e => { e.preventDefault(); pozewUploadZone.classList.add('dragover'); });
    pozewUploadZone.addEventListener('dragleave', () => pozewUploadZone.classList.remove('dragover'));
    pozewUploadZone.addEventListener('drop', e => {
        e.preventDefault();
        pozewUploadZone.classList.remove('dragover');
        handlePozewFiles(e.dataTransfer.files);
    });
}

if (pozewFileInput) {
    pozewFileInput.addEventListener('change', e => handlePozewFiles(e.target.files));
}

function handlePozewFiles(files) {
    pozewUploadedFiles = [...pozewUploadedFiles, ...Array.from(files)];
    renderPozewFileList();
    updatePozewOcrButton();
}

function renderPozewFileList() {
    if (!pozewFileList) return;
    pozewFileList.innerHTML = pozewUploadedFiles.map((f, i) => `
        <div class="file-item">
            <span class="file-name">${f.name}</span>
            <button class="file-remove" onclick="removePozewFile(${i})">✕</button>
        </div>
    `).join('');
}

window.removePozewFile = function (index) {
    pozewUploadedFiles.splice(index, 1);
    renderPozewFileList();
    updatePozewOcrButton();
};

function updatePozewOcrButton() {
    if (btnPozewOcr) btnPozewOcr.disabled = pozewUploadedFiles.length === 0;
}

// Pozew OCR processing
if (btnPozewOcr) {
    btnPozewOcr.addEventListener('click', async () => {
        if (pozewUploadedFiles.length === 0) return;

        const btnIcon = document.getElementById('btnPozewOcrIcon');
        const btnText = document.getElementById('btnPozewOcrText');
        const progressBar = document.getElementById('pozewOcrProgressBar');
        const progressFill = document.getElementById('pozewOcrProgressFill');
        const statusText = document.getElementById('pozewOcrStatusText');

        btnPozewOcr.disabled = true;
        if (btnIcon) btnIcon.innerHTML = '<span class="spinner">⏳</span>';
        if (btnText) btnText.textContent = 'Przetwarzanie...';
        if (progressBar) progressBar.classList.remove('hidden');
        if (statusText) { statusText.classList.remove('hidden'); statusText.textContent = '📷 OCR wezwania...'; }
        if (progressFill) progressFill.style.width = '20%';

        const formData = new FormData();
        pozewUploadedFiles.forEach(f => formData.append('files', f));
        formData.append('template', 'wezwanie_do_zaplaty.html');

        try {
            const response = await fetch('/api/process_ocr', { method: 'POST', body: formData });
            if (progressFill) progressFill.style.width = '80%';
            const data = await response.json();

            if (data.success && data.documents?.length > 0) {
                if (statusText) statusText.textContent = '✅ Dane z wezwania pobrane!';
                if (progressFill) progressFill.style.width = '100%';

                // Pokaż dane
                if (extractedDataCard) extractedDataCard.classList.remove('hidden');
                if (extractedDataContent) extractedDataContent.textContent = JSON.stringify(data.documents, null, 2);

                // Wyczyść
                pozewUploadedFiles = [];
                renderPozewFileList();
            } else {
                if (statusText) statusText.textContent = '⚠️ Brak danych';
            }
        } catch (e) {
            if (statusText) statusText.textContent = `❌ ${e.message}`;
        } finally {
            if (btnIcon) btnIcon.textContent = '🚀';
            if (btnText) btnText.textContent = 'OCR wezwania';
            updatePozewOcrButton();
            setTimeout(() => progressBar?.classList.add('hidden'), 3000);
        }
    });
}
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

// ==================== QUICK OCR - NOWY WORKFLOW ====================
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

// Nowe elementy workflow
const stepWezwanie = document.getElementById('stepWezwanie');
const stepPozew = document.getElementById('stepPozew');
const dividerStep2 = document.getElementById('dividerStep2');
const wezwaniaList = document.getElementById('wezwaniaList');
const refreshWezwaniaList = document.getElementById('refreshWezwaniaList');
const saveWezwanieSection = document.getElementById('saveWezwanieSection');
const btnSaveWezwanie = document.getElementById('btnSaveWezwanie');

// KRS elements
const btnKrsPowodUpload = document.getElementById('btnKrsPowodUpload');
const btnKrsPowodManual = document.getElementById('btnKrsPowodManual');
const krsPowodFile = document.getElementById('krsPowodFile');
const krsPowodManualFields = document.getElementById('krsPowodManualFields');
const krsPowodUploadStatus = document.getElementById('krsPowodUploadStatus');

let quickFiles = [];
let selectedWezwania = [];
let currentWorkflowType = null; // 'wezwanie' or 'pozew'

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

// === TEMPLATE SELECTION - WORKFLOW BRANCHING ===
quickTemplateSelect.addEventListener('change', function () {
    const template = this.value;

    // Hide all step 2 sections
    stepWezwanie.classList.add('hidden');
    stepPozew.classList.add('hidden');
    dividerStep2.classList.add('hidden');
    btnQuickProcess.classList.add('hidden');

    if (!template) {
        currentWorkflowType = null;
        return;
    }

    dividerStep2.classList.remove('hidden');
    btnQuickProcess.classList.remove('hidden');

    if (template.includes('wezwanie')) {
        // Workflow: Wezwanie do Zapłaty
        currentWorkflowType = 'wezwanie';
        stepWezwanie.classList.remove('hidden');
        btnQuickText.textContent = 'Przetwórz fakturę';
    } else if (template.includes('pozew')) {
        // Workflow: Pozew
        currentWorkflowType = 'pozew';
        stepPozew.classList.remove('hidden');
        btnQuickText.textContent = 'Generuj pozew';
        loadWezwaniaList();
    }

    updateQuickButton();
});

// === WEZWANIA LIST ===
async function loadWezwaniaList() {
    try {
        const response = await fetch('/api/wezwania');
        const wezwania = await response.json();

        if (wezwania.length === 0) {
            wezwaniaList.innerHTML = `
                <div style="color: var(--text-muted); padding: 16px; text-align: center;">
                    Brak zapisanych wezwań. Najpierw wygeneruj Wezwanie do Zapłaty.
                </div>`;
        } else {
            wezwaniaList.innerHTML = wezwania.map(w => `
                <div class="wezwanie-item">
                    <input type="checkbox" id="wezwanie_${w.id}" value="${w.id}" 
                        onchange="toggleWezwanieSelection('${w.id}')">
                    <div class="wezwanie-info">
                        <div class="wezwanie-dluznik">${w.dluznik_nazwa}</div>
                        <div class="wezwanie-details">
                            Faktura: ${w.faktura_numer} | Kwota: ${w.kwota} | 
                            ${new Date(w.created_at).toLocaleDateString('pl-PL')}
                        </div>
                    </div>
                </div>
            `).join('');
        }
    } catch (e) {
        console.error('Error loading wezwania:', e);
        wezwaniaList.innerHTML = '<div style="color: red; padding: 16px;">Błąd ładowania wezwań</div>';
    }
}

window.toggleWezwanieSelection = function (id) {
    const index = selectedWezwania.indexOf(id);
    if (index > -1) {
        selectedWezwania.splice(index, 1);
    } else {
        selectedWezwania.push(id);
    }
    updateQuickButton();
};

if (refreshWezwaniaList) {
    refreshWezwaniaList.addEventListener('click', loadWezwaniaList);
}

// === KRS HANDLING ===
if (btnKrsPowodUpload) {
    btnKrsPowodUpload.addEventListener('click', () => {
        krsPowodFile.click();
    });
}

if (btnKrsPowodManual) {
    btnKrsPowodManual.addEventListener('click', () => {
        krsPowodManualFields.classList.toggle('hidden');
        btnKrsPowodManual.classList.toggle('active');
        krsPowodUploadStatus.classList.add('hidden');
        krsPowodFileData = null;
    });
}

if (krsPowodFile) {
    krsPowodFile.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            krsPowodFileData = e.target.files[0];
            krsPowodUploadStatus.classList.remove('hidden');
            krsPowodUploadStatus.textContent = `✅ Plik KRS załadowany: ${krsPowodFileData.name}`;
            krsPowodManualFields.classList.add('hidden');
            btnKrsPowodManual.classList.remove('active');
        }
    });
}

// === UPLOAD ZONE EVENTS ===
if (quickUploadZone) {
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
}

if (quickFileInput) {
    quickFileInput.addEventListener('change', (e) => {
        handleQuickFiles(e.target.files);
    });
}

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
    if (!btnQuickProcess) return;

    if (currentWorkflowType === 'wezwanie') {
        btnQuickProcess.disabled = quickFiles.length === 0;
    } else if (currentWorkflowType === 'pozew') {
        btnQuickProcess.disabled = selectedWezwania.length === 0;
    } else {
        btnQuickProcess.disabled = true;
    }
}

// === PROCESS BUTTON ===
if (btnQuickProcess) {
    btnQuickProcess.addEventListener('click', async () => {
        if (currentWorkflowType === 'wezwanie') {
            await processWezwanie();
        } else if (currentWorkflowType === 'pozew') {
            await processPozew();
        }
    });
}

// === WEZWANIE PROCESSING ===
async function processWezwanie() {
    if (quickFiles.length === 0) return;

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
            await showFilledTemplate(data.template, data.fields, 'wezwanie');
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
        btnQuickText.textContent = 'Przetwórz fakturę';
        updateQuickButton();

        setTimeout(() => {
            quickProgressBar.classList.add('hidden');
        }, 2000);
    }
}

// === POZEW PROCESSING ===
async function processPozew() {
    if (selectedWezwania.length === 0) return;

    btnQuickProcess.disabled = true;
    btnQuickProcess.classList.add('loading');
    btnQuickIcon.innerHTML = '<span class="spinner">⏳</span>';
    btnQuickText.textContent = 'Generowanie pozwu...';
    quickProgressBar.classList.remove('hidden');
    quickStatusText.classList.remove('hidden');
    quickStatusText.textContent = '📋 Pobieranie danych z wezwań...';
    quickProgressFill.style.width = '20%';
    quickResultCard.classList.add('hidden');

    try {
        // Get summary from selected wezwania
        const summaryResponse = await fetch('/api/wezwania/summary', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ids: selectedWezwania })
        });

        const summaryData = await summaryResponse.json();
        quickProgressFill.style.width = '50%';

        if (!summaryData.success) {
            throw new Error(summaryData.error);
        }

        // Collect manual KRS data
        const krsPowod = {};
        if (krsPowodManualFields && !krsPowodManualFields.classList.contains('hidden')) {
            krsPowod.nazwa = document.querySelector('input[name="powod_nazwa_pelna"]')?.value || '';
            krsPowod.adres = document.querySelector('input[name="powod_adres_pelny"]')?.value || '';
            krsPowod.krs = document.querySelector('input[name="powod_numer_krs"]')?.value || '';
        }

        const pozwanyOznaczenie = document.querySelector('input[name="pozwany_oznaczenie_pelne"]')?.value || '';

        quickStatusText.textContent = '📄 Ładowanie szablonu pozwu...';
        quickProgressFill.style.width = '70%';

        // Prepare fields for pozew
        const fields = {
            platnosc_kwota_glowna: summaryData.summary.total_amount_formatted,
            roszczenie_kwota_glowna: summaryData.summary.total_amount_formatted,
            powod_nazwa_pelna: krsPowod.nazwa,
            powod_adres_pelny: krsPowod.adres,
            powod_numer_krs: krsPowod.krs,
            pozwany_oznaczenie_pelne: pozwanyOznaczenie
        };

        // Add invoice data from first wezwanie
        if (summaryData.summary.invoices.length > 0) {
            const inv = summaryData.summary.invoices[0];
            fields.dowod_faktura_numer = inv.numer;
            fields.dowod_faktura_data_wystawienia = inv.data;
            fields.roszczenie_odsetki_data_poczatkowa = inv.termin;
        }

        quickProgressFill.style.width = '100%';
        quickStatusText.textContent = '✅ Zakończono!';

        await showFilledTemplate(quickTemplateSelect.value, fields, 'pozew');

    } catch (error) {
        quickStatusText.textContent = `❌ ${error.message}`;
    } finally {
        btnQuickProcess.classList.remove('loading');
        btnQuickIcon.textContent = '🚀';
        btnQuickText.textContent = 'Generuj pozew';
        updateQuickButton();

        setTimeout(() => {
            quickProgressBar.classList.add('hidden');
        }, 2000);
    }
}

// === SHOW FILLED TEMPLATE ===
async function showFilledTemplate(templateFilename, fields, docType) {
    const templateResponse = await fetch(`/api/template/${templateFilename}`);
    const templateData = await templateResponse.json();

    quickResultCard.classList.remove('hidden');
    quickPreview.innerHTML = '';

    // Show save button only for wezwanie
    if (docType === 'wezwanie') {
        saveWezwanieSection.classList.remove('hidden');
    } else {
        saveWezwanieSection.classList.add('hidden');
    }

    const iframe = document.createElement('iframe');
    iframe.style.width = '100%';
    iframe.style.height = '600px';
    iframe.style.border = 'none';
    iframe.id = 'documentIframe';
    quickPreview.appendChild(iframe);

    iframe.contentDocument.open();
    iframe.contentDocument.write(templateData.content);

    // Inject scrollbar styles
    const style = iframe.contentDocument.createElement('style');
    style.textContent = `
        body::-webkit-scrollbar { width: 8px; }
        body::-webkit-scrollbar-track { background: #f1f1f1; }
        body::-webkit-scrollbar-thumb { background: #888; border-radius: 4px; }
        body::-webkit-scrollbar-thumb:hover { background: #555; }
        body { scrollbar-width: thin; scrollbar-color: #888 #f1f1f1; }
    `;
    iframe.contentDocument.head.appendChild(style);
    iframe.contentDocument.close();

    // Fill inputs after a short delay
    setTimeout(() => {
        const doc = iframe.contentDocument;
        const skipFields = ['dokument_miejscowosc_data', 'meta_miejscowosc_data_dokumentu'];

        for (const [fieldName, value] of Object.entries(fields)) {
            if (skipFields.includes(fieldName) || !value) continue;

            const inputs = doc.querySelectorAll(`input[name="${fieldName}"]`);
            inputs.forEach(input => {
                input.value = value;
                input.style.background = '#e8f5e9';
            });
        }
    }, 100);
}

// === SAVE WEZWANIE ===
if (btnSaveWezwanie) {
    btnSaveWezwanie.addEventListener('click', async () => {
        const iframe = document.getElementById('documentIframe');
        if (!iframe) {
            alert('Brak dokumentu do zapisania!');
            return;
        }

        const doc = iframe.contentDocument;
        const fields = {};

        // Collect all input values
        doc.querySelectorAll('input[name]').forEach(input => {
            fields[input.name] = input.value;
        });

        try {
            const response = await fetch('/api/wezwania/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ fields })
            });

            const result = await response.json();

            if (result.success) {
                alert(`✅ Wezwanie zapisane!\nID: ${result.id}`);
                saveWezwanieSection.innerHTML = `
                    <p style="margin: 0; color: #2e7d32; font-weight: 500;">
                        ✅ Wezwanie zapisane (ID: ${result.id})
                    </p>`;
            } else {
                alert(`❌ Błąd: ${result.error}`);
            }
        } catch (e) {
            alert(`❌ Błąd zapisu: ${e.message}`);
        }
    });
}

// ==================== PRINT TO PDF ====================
const btnPrintPdf = document.getElementById('btnPrintPdf');

if (btnPrintPdf) {
    btnPrintPdf.addEventListener('click', () => {
        const iframe = quickPreview.querySelector('iframe');

        if (!iframe || !iframe.contentWindow) {
            alert('Brak dokumentu do wydrukowania!');
            return;
        }

        iframe.contentWindow.focus();
        iframe.contentWindow.print();
    });
}

// ==================== POZEW - KRS UPLOADS ====================

const krsPowodUploadZone = document.getElementById('krsPowodUploadZone');
const advKrsPowodFile = document.getElementById('advKrsPowodFile');
const advKrsPowodUploadStatus = document.getElementById('advKrsPowodUploadStatus');
const krsPozwanyUploadZone = document.getElementById('krsPozwanyUploadZone');
const advKrsPozwanyFile = document.getElementById('advKrsPozwanyFile');
const advKrsPozwanyUploadStatus = document.getElementById('advKrsPozwanyUploadStatus');
const btnProcessPozew = document.getElementById('btnProcessPozew');
const pozewProgressBar = document.getElementById('pozewProgressBar');
const pozewProgressFill = document.getElementById('pozewProgressFill');
const pozewStatusText = document.getElementById('pozewStatusText');

let krsPowodFileData = null;
let krsPozwanyFileData = null;

// KRS Powoda upload
if (krsPowodUploadZone && advKrsPowodFile) {
    krsPowodUploadZone.addEventListener('click', () => advKrsPowodFile.click());
    krsPowodUploadZone.addEventListener('dragover', (e) => { e.preventDefault(); krsPowodUploadZone.classList.add('dragover'); });
    krsPowodUploadZone.addEventListener('dragleave', () => krsPowodUploadZone.classList.remove('dragover'));
    krsPowodUploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        krsPowodUploadZone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            advKrsPowodFile.files = e.dataTransfer.files;
            handleKrsPowodFile(e.dataTransfer.files[0]);
        }
    });
    advKrsPowodFile.addEventListener('change', () => {
        if (advKrsPowodFile.files.length > 0) {
            handleKrsPowodFile(advKrsPowodFile.files[0]);
        }
    });
}

function handleKrsPowodFile(file) {
    krsPowodFileData = file;
    if (advKrsPowodUploadStatus) {
        advKrsPowodUploadStatus.classList.remove('hidden');
        advKrsPowodUploadStatus.innerHTML = `✅ KRS Powoda: ${file.name}`;
    }
}

// KRS Pozwanego upload
if (krsPozwanyUploadZone && advKrsPozwanyFile) {
    krsPozwanyUploadZone.addEventListener('click', () => advKrsPozwanyFile.click());
    krsPozwanyUploadZone.addEventListener('dragover', (e) => { e.preventDefault(); krsPozwanyUploadZone.classList.add('dragover'); });
    krsPozwanyUploadZone.addEventListener('dragleave', () => krsPozwanyUploadZone.classList.remove('dragover'));
    krsPozwanyUploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        krsPozwanyUploadZone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            advKrsPozwanyFile.files = e.dataTransfer.files;
            handleKrsPozwanyFile(e.dataTransfer.files[0]);
        }
    });
    advKrsPozwanyFile.addEventListener('change', () => {
        if (advKrsPozwanyFile.files.length > 0) {
            handleKrsPozwanyFile(advKrsPozwanyFile.files[0]);
        }
    });
}

function handleKrsPozwanyFile(file) {
    krsPozwanyFileData = file;
    if (advKrsPozwanyUploadStatus) {
        advKrsPozwanyUploadStatus.classList.remove('hidden');
        advKrsPozwanyUploadStatus.innerHTML = `✅ KRS Pozwanego: ${file.name}`;
    }
}

// ==================== POZEW - PRZETWARZANIE ====================

if (btnProcessPozew) {
    btnProcessPozew.addEventListener('click', async () => {
        // Sprawdź czy wybrano wezwania
        if (selectedAdvWezwania.length === 0) {
            alert('Wybierz co najmniej jedno wezwanie do zapłaty!');
            return;
        }

        btnProcessPozew.disabled = true;
        const btnIcon = document.getElementById('btnProcessPozewIcon');
        const btnText = document.getElementById('btnProcessPozewText');
        if (btnIcon) btnIcon.textContent = '⏳';
        if (btnText) btnText.textContent = 'Przetwarzanie...';
        if (pozewProgressBar) pozewProgressBar.classList.remove('hidden');
        if (pozewStatusText) pozewStatusText.classList.remove('hidden');

        try {
            let progress = 0;
            const updateProgress = (val, text) => {
                progress = val;
                if (pozewProgressFill) pozewProgressFill.style.width = `${val}%`;
                if (pozewStatusText) pozewStatusText.textContent = text;
            };

            updateProgress(10, '📂 Pobieranie danych z wezwań...');

            // 1. Pobierz dane z wybranych wezwań
            const summaryResponse = await fetch('/api/wezwania/summary', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ids: selectedAdvWezwania })
            });
            const summaryData = await summaryResponse.json();

            updateProgress(30, '🔄 Przetwarzanie KRS powoda przez OCR...');

            // 2. Przetwórz KRS powoda (jeśli wgrany)
            let krsPowodData = {};
            if (krsPowodFileData) {
                const formData = new FormData();
                formData.append('file', krsPowodFileData);
                const ocrRes = await fetch('/api/ocr', { method: 'POST', body: formData });
                const ocrResult = await ocrRes.json();
                if (ocrResult.success) {
                    // TODO: Przetwórz OCR przez LLM dla KRS
                    krsPowodData = { filename: ocrResult.filename };
                }
            }

            updateProgress(50, '🔄 Przetwarzanie KRS pozwanego przez OCR...');

            // 3. Przetwórz KRS pozwanego (jeśli wgrany)
            let krsPozwanyData = {};
            if (krsPozwanyFileData) {
                const formData = new FormData();
                formData.append('file', krsPozwanyFileData);
                const ocrRes = await fetch('/api/ocr', { method: 'POST', body: formData });
                const ocrResult = await ocrRes.json();
                if (ocrResult.success) {
                    // TODO: Przetwórz OCR przez LLM dla KRS
                    krsPozwanyData = { filename: ocrResult.filename };
                }
            }

            updateProgress(70, '📝 Wypełnianie szablonu pozwu...');

            // 4. Wypełnij szablon pozwu danymi
            if (templateIframe && templateIframe.contentDocument) {
                const doc = templateIframe.contentDocument;

                // Wypełnij danymi z wezwań
                if (summaryData.wezwania && summaryData.wezwania.length > 0) {
                    const w = summaryData.wezwania[0]; // Użyj pierwszego wezwania jako głównego źródła

                    // Dane pozwanego (dłużnika) z wezwania
                    fillInput(doc, 'pozwany_nazwa_pelna', w.fields?.dluznik_nazwa || w.dluznik_nazwa || '');
                    fillInput(doc, 'pozwany_adres_pelny', w.fields?.dluznik_adres || w.dluznik_adres || '');
                    fillInput(doc, 'pozwany_numer_krs', ''); // KRS z OCR lub pusty

                    // Dane powoda (wierzyciela)
                    fillInput(doc, 'powod_nazwa_pelna', w.fields?.wierzyciel_nazwa || '');
                    fillInput(doc, 'powod_adres_pelny', w.fields?.wierzyciel_adres || '');

                    // Kwota
                    fillInput(doc, 'wartosc_przedmiotu_sporu', summaryData.total_amount_formatted || '');
                }
            }

            updateProgress(100, '✅ Pozew wypełniony!');

        } catch (error) {
            if (pozewStatusText) pozewStatusText.textContent = `❌ Błąd: ${error.message}`;
        } finally {
            btnProcessPozew.disabled = false;
            if (btnIcon) btnIcon.textContent = '⚖️';
            if (btnText) btnText.textContent = 'Przetwórz i wypełnij pozew';
        }
    });
}

function fillInput(doc, name, value) {
    const inputs = doc.querySelectorAll(`input[name="${name}"]`);
    inputs.forEach(input => {
        input.value = value;
        input.style.background = '#e8f5e9';
    });
}
