// ==================== Templates - ADVANCED MODE ====================
const templateSelect = document.getElementById('templateSelect');
const templatePreview = document.getElementById('templatePreview');
const extractedDataCard = document.getElementById('extractedDataCard');
const extractedDataContent = document.getElementById('extractedDataContent');
const advActionsCard = document.getElementById('advActionsCard');

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
                        <strong>${w.dluznik_nazwa}</strong>
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

    // Explicitly update calling generated button state if necessary
    if (typeof updateGeneratePozewButton === 'function') {
        updateGeneratePozewButton();
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
    updateAdvOcrButton();
    if (advFileInput) advFileInput.value = '';
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
    updateAdvOcrButton();
};

function updateAdvOcrButton() {
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
        const ocrFillProgressText = document.getElementById('ocrFillProgressText');
        const advBtnSaveToLibrary = document.getElementById('advBtnSaveToLibrary');
        const btnPrintTemplate = document.getElementById('btnPrintTemplate');
        const btnExportExcel = document.getElementById('btnExportExcel');

        btnOcrFill.disabled = true;
        btnOcrFill.classList.add('loading');
        if (btnOcrFillIcon) btnOcrFillIcon.innerHTML = '<span class="spinner">⏳</span>';
        if (btnOcrFillText) btnOcrFillText.textContent = 'Trwa analiza...';
        
        if (ocrFillProgressBar) ocrFillProgressBar.classList.remove('hidden');
        if (ocrFillProgressText) {
            ocrFillProgressText.classList.remove('hidden');
            ocrFillProgressText.textContent = `Przygotowywanie... (0 / ${advUploadedFiles.length})`;
        }
        if (ocrFillProgressFill) {
            ocrFillProgressFill.style.width = '0%';
            ocrFillProgressFill.classList.add('animating');
        }

        // Reset actions state
        if (advBtnSaveToLibrary) advBtnSaveToLibrary.disabled = true;
        if (btnPrintTemplate) btnPrintTemplate.disabled = true;
        if (btnExportExcel) btnExportExcel.disabled = true;

        const allDocuments = [];
        const allProcessedFiles = [];
        const templateName = templateSelect ? templateSelect.value : '';

        try {
            if (advWorkflowType === 'podsumowanie') {
                // Pobierz zaznaczone kolumny z checkboxów (obsługa data-columns + switch netto)
                const _nettoSw = document.getElementById('nettoSwitch');
                const _nettoOn = !_nettoSw || _nettoSw.checked;
                const selectedColumns = Array.from(document.querySelectorAll('#columnToggleList input:checked'))
                    .flatMap(cb => {
                        const cols = (cb.dataset.columns || '').split(',').map(s => s.trim()).filter(Boolean);
                        if (!_nettoOn && cols.length === 2) return [cols[1]];
                        return cols;
                    });

                // SEQUENTIAL PROCESSING FOR PODSUMOWANIE (Real Progress Bar)
                for (let i = 0; i < advUploadedFiles.length; i++) {
                    const file = advUploadedFiles[i];
                    if (ocrFillProgressText) {
                        ocrFillProgressText.textContent = `Przetwarzanie: ${file.name} (${i + 1} / ${advUploadedFiles.length})`;
                    }

                    const formData = new FormData();
                    formData.append('files', file);
                    if (templateName) formData.append('template', templateName);
                    formData.append('selected_columns', selectedColumns.join(','));

                    try {
                        const response = await fetch('/api/process_ocr', {
                            method: 'POST',
                            body: formData
                        });
                        const data = await response.json();

                        if (data.success && data.documents) {
                            allDocuments.push(...data.documents);
                            if (data.processed) allProcessedFiles.push(...data.processed);
                        }
                    } catch (err) {
                        console.error(`Error processing file ${file.name}:`, err);
                    }

                    // Update Progress
                    if (ocrFillProgressFill) {
                        const percent = Math.round(((i + 1) / advUploadedFiles.length) * 100);
                        ocrFillProgressFill.style.width = `${percent}%`;
                    }
                }

                window.lastProcessedDocuments = allDocuments;
                window.lastProcessedFiles = allProcessedFiles;

                if (allDocuments.length > 0) {
                    renderDynamicTable(allDocuments);
                }
            } else {
                // BATCH PROCESSING FOR OTHER TYPES (Standard Flow)
                const formData = new FormData();
                advUploadedFiles.forEach(file => formData.append('files', file));
                if (templateName) formData.append('template', templateName);

                if (ocrFillProgressFill) ocrFillProgressFill.style.width = '20%';
                if (ocrFillProgressText) {
                    ocrFillProgressText.classList.remove('hidden');
                    ocrFillProgressText.textContent = 'Trwa wysyłanie plików...';
                }

                const response = await fetch('/api/process_ocr', {
                    method: 'POST',
                    body: formData
                });
                
                if (ocrFillProgressFill) ocrFillProgressFill.style.width = '70%';
                if (ocrFillProgressText) ocrFillProgressText.textContent = 'Analizowanie wyników...';
                
                const data = await response.json();
                
                if (ocrFillProgressFill) ocrFillProgressFill.style.width = '100%';
                if (ocrFillProgressText) ocrFillProgressText.textContent = 'Zakończono!';

                if (data.success && data.documents) {
                    // This part remains as it was in original advanced.js for 'wezwanie'/'pozew'
                    // but logic is omitted here for brevity as it's handled below in finally/data check
                    // actually I should keep the logic for other types too.
                    
                    // (Simplified logic for other types to keep the file consistent)
                    if (advWorkflowType === 'podsumowanie') {
                        // Already handled above
                    } else {
                        // Logic for 'wezwanie' aggregation should go here
                        // For now I'll redirect to the data block if needed
                        processStandardWorkflowData(data);
                    }
                }
            }

            // After completion
            if (advBtnSaveToLibrary) advBtnSaveToLibrary.disabled = false;
            if (btnPrintTemplate) btnPrintTemplate.disabled = false;
            if (btnExportExcel) btnExportExcel.disabled = (allProcessedFiles.length === 0 && !window.lastProcessedFiles);

            if (advActionsCard) advActionsCard.classList.remove('hidden');

            // Hide analysis actions if completed successfully
            const analysisActions = document.getElementById('analysis-actions');
            if (analysisActions && advWorkflowType === 'podsumowanie') {
                 // Optionally hide the button after success
                 // analysisActions.classList.add('hidden');
            }

        } catch (error) {
            console.error('OCR Processing Error:', error);
        } finally {
            btnOcrFill.classList.remove('loading');
            if (btnOcrFillIcon) btnOcrFillIcon.textContent = '🚀';
            if (btnOcrFillText) btnOcrFillText.textContent = 'Analiza zakończona';
            
            // Keep progress bar for a moment
            setTimeout(() => {
                // if (ocrFillProgressBar) ocrFillProgressBar.classList.add('hidden');
                // if (ocrFillProgressText) ocrFillProgressText.classList.add('hidden');
            }, 5000);
        }
    });
}

// Helper to keep original logic for 'wezwanie' and 'pozew'
function processStandardWorkflowData(data) {
    if (!data.documents || data.documents.length === 0) return;
    
    // Agreguj dane z wielu dokumentów (moved from original btnOcrFill listener)
    const invoiceNumbers = [];
    const invoiceDates = [];
    let totalAmount = 0;
    let latestPaymentDate = null;
    let latestPaymentDateStr = '';
    const mergedFields = {};

    const amountFieldPattern = /kwot/i;
    const invoiceNumPattern = /numer_faktury/i;
    const paymentDatePattern = /terminu_platnosci|date_terminu/i;
    const invoiceDatePattern = /date_wystawienia/i;

    data.documents.forEach(doc => {
        const fields = doc.fields || {};
        for (let [key, value] of Object.entries(fields)) {
            if (!value) continue;
            if (invoiceNumPattern.test(key)) {
                if (!invoiceNumbers.includes(value)) invoiceNumbers.push(value);
            } else if (amountFieldPattern.test(key)) {
                const numStr = String(value).replace(/[^\d,.]/g, '').replace(',', '.');
                const num = parseFloat(numStr);
                if (!isNaN(num)) totalAmount += num;
            } else if (invoiceDatePattern.test(key)) {
                if (!invoiceDates.includes(value)) invoiceDates.push(value);
            } else if (paymentDatePattern.test(key)) {
                const parsed = parsePolishDate(value);
                if (parsed && (!latestPaymentDate || parsed > latestPaymentDate)) {
                    latestPaymentDate = parsed;
                    latestPaymentDateStr = value;
                }
            } else if (!mergedFields[key]) {
                mergedFields[key] = value;
            }
        }
    });

    if (templateIframe && templateIframe.contentDocument) {
        const doc = templateIframe.contentDocument;
        for (let [fieldName, value] of Object.entries(mergedFields)) {
            const inputs = doc.querySelectorAll(`input[name="${fieldName}"]`);
            inputs.forEach(input => { input.value = value; input.style.background = '#e8f5e9'; });
        }
        const invoiceInputs = doc.querySelectorAll('input[name*="numer_faktury"]');
        invoiceInputs.forEach(input => { input.value = invoiceNumbers.join(', '); input.style.background = '#e3f2fd'; });
        const dateInputs = doc.querySelectorAll('input[name*="date_wystawienia"]');
        dateInputs.forEach(input => { input.value = invoiceDates.join(', '); input.style.background = '#e8f5e9'; });
        const amountInputs = doc.querySelectorAll('input[name*="kwot"]');
        amountInputs.forEach(input => { input.value = totalAmount.toFixed(2) + ' zł'; input.style.background = '#fff3e0'; });
        if (latestPaymentDateStr) {
            const nextDay = addOneDay(latestPaymentDateStr);
            const paymentInputs = doc.querySelectorAll('input[name*="terminu_platnosci"], input[name*="date_terminu"]');
            paymentInputs.forEach(input => { input.value = nextDay; input.style.background = '#fce4ec'; });
        }
    }
}

// parsePolishDate is defined in helpers.js

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

                            // parsePolishDate is defined in helpers.js

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

                        // findMatchingInputs is defined in helpers.js

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

// Połącz powiązania z Sidebarem (Paskiem bocznym)
document.addEventListener('DOMContentLoaded', () => {
    const sidebarNav = document.getElementById('sidebarTemplateNav');
    if (sidebarNav && templateSelect) {
        const navItems = sidebarNav.querySelectorAll('.nav-item');

        navItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const templateFile = item.getAttribute('data-template');
                if (templateFile) {
                    // Update Page Title
                    updateHeaderTitle(item.title);

                    // Odznacz wszystkie
                    navItems.forEach(nav => nav.classList.remove('active'));
                    // Zaznacz kliknięty
                    item.classList.add('active');

                    // Ukryj welcome screen i bibliotekę
                    const welcome = document.getElementById('dashboard-welcome');
                    const library = document.getElementById('dashboard-library');
                    const advanced = document.getElementById('dashboard-advanced');
                    if (welcome) welcome.classList.add('hidden');
                    if (library) library.classList.add('hidden');
                    if (advanced) advanced.classList.remove('hidden');

                    // Add header padding when in template
                    const header = document.querySelector('.dashboard-header');
                    if (header) header.classList.add('header-padded');

                    // Zmień wartość ukrytego selecta i wywołaj event zmiany
                    templateSelect.value = templateFile;
                    templateSelect.dispatchEvent(new Event('change'));
                }
            });
        });
    }

    // Logo Click -> Go to Welcome Screen
    const sidebarLogo = document.getElementById('sidebar-logo');
    if (sidebarLogo) {
        sidebarLogo.addEventListener('click', () => {
            // Update Page Title
            updateHeaderTitle("");

            // Odznacz wszystkie nav
            const navItems = document.querySelectorAll('.nav-item');
            navItems.forEach(nav => nav.classList.remove('active'));

            // View Switch
            const welcome = document.getElementById('dashboard-welcome');
            const library = document.getElementById('dashboard-library');
            const advanced = document.getElementById('dashboard-advanced');

            if (welcome) welcome.classList.remove('hidden');
            if (library) library.classList.add('hidden');
            if (advanced) advanced.classList.add('hidden');

            // Remove header padding on welcome
            const header = document.querySelector('.dashboard-header');
            if (header) header.classList.remove('header-padded');
        });
    }
});

if (templateSelect) {
    templateSelect.addEventListener('change', async function () {
        const filename = this.value;

        // Hide all step sections
        const advStepUpload = document.getElementById('advStepUpload');
        const advPreviewCard = document.getElementById('advPreviewCard');
        const advActionsCard = document.getElementById('advActionsCard');
        const podsumowanieSettings = document.getElementById('podsumowanieSettings');
        const podsumowanieExtraOptions = document.getElementById('podsumowanieExtraOptions');
        if (podsumowanieSettings) podsumowanieSettings.classList.add('hidden');
        if (podsumowanieExtraOptions) podsumowanieExtraOptions.classList.add('hidden');
        if (advStepSource) advStepSource.classList.add('hidden');
        if (advStepSourcePozew) advStepSourcePozew.classList.add('hidden');
        if (advStepLlm) advStepLlm.classList.add('hidden');
        if (advStepPozewExtra) advStepPozewExtra.classList.add('hidden');
        if (advDividerStep2) advDividerStep2.classList.add('hidden');
        if (advDividerStep3) advDividerStep3.classList.add('hidden');

        // Reset button states
        if (advStepUpload) advStepUpload.classList.add('hidden');
        if (advPreviewCard) {
            advPreviewCard.classList.add('hidden');
            // Reset styling classes
            advPreviewCard.classList.remove('card-white', 'card-beige');
            advPreviewCard.classList.add('card-purple');
        }
        if (advActionsCard) advActionsCard.classList.add('hidden');

        const btnSaveLib = document.getElementById('advBtnSaveToLibrary');
        if (btnSaveLib) btnSaveLib.disabled = true;

        if (!filename) {
            advWorkflowType = null;
            if (templatePreview) templatePreview.innerHTML = '<div style="padding: 48px; text-align: center; color: var(--text-muted);">Wybierz szablon aby zobaczyć podgląd</div>';
            currentTemplateFields = [];
            return;
        }

        // Show workflow sections based on template type
        if (advDividerStep2) advDividerStep2.classList.remove('hidden');
        if (advPreviewCard) advPreviewCard.classList.remove('hidden');
        if (advActionsCard) advActionsCard.classList.remove('hidden');

        if (filename.includes('wezwanie')) {
            advWorkflowType = 'wezwanie';
            // Dla wezwania - pokaż sekcję upload
            if (advStepUpload) advStepUpload.classList.remove('hidden');
        } else if (filename.includes('pozew')) {
            advWorkflowType = 'pozew';
            // Dla pozwu - pokaż sekcję z wezwaniami, ukryj upload
            if (advStepSourcePozew) advStepSourcePozew.classList.remove('hidden');
            if (advStepPozewExtra) advStepPozewExtra.classList.remove('hidden');

            // Załaduj listę wezwań
            loadAdvWezwaniaList();
        } else if (filename.includes('podsumowanie')) {
            advWorkflowType = 'podsumowanie';
            // Pokaż sekcję upload dla podsumowania
            if (advStepUpload) advStepUpload.classList.remove('hidden');
            // Pokaż ustawienia kolumn
            const podsumowanieSettings = document.getElementById('podsumowanieSettings');
            const podsumowanieExtraOptions = document.getElementById('podsumowanieExtraOptions');
            if (podsumowanieSettings) podsumowanieSettings.classList.remove('hidden');
            if (podsumowanieExtraOptions) podsumowanieExtraOptions.classList.remove('hidden');
            // Stylizacja dla podsumowania: wywal fioletowe
            if (advPreviewCard) {
                advPreviewCard.classList.remove('card-purple');
                advPreviewCard.classList.add('card-white');
            }
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
                templateIframe.style.height = '100%';
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
                // Keep disabled until analysis is complete
                btnPrint.disabled = true;
                btnPrint.onclick = function () {
                    if (templateIframe && templateIframe.contentWindow) {
                        templateIframe.contentWindow.focus();
                        templateIframe.contentWindow.print();
                    }
                };
            }

            const btnSaveLib = document.getElementById('advBtnSaveToLibrary');
            if (btnSaveLib) btnSaveLib.disabled = true;

            const btnExportExcel = document.getElementById('btnExportExcel');
            if (btnExportExcel) btnExportExcel.disabled = true;

        } catch (e) {
            if (templatePreview) templatePreview.innerHTML = '<div style="padding: 48px; text-align: center; color: #ff453a;">Błąd ładowania szablonu</div>';
        }
    });

    const advBtnSaveToLibrary = document.getElementById('advBtnSaveToLibrary');
    if (advBtnSaveToLibrary) {
        advBtnSaveToLibrary.addEventListener('click', async () => {
            if (!templateIframe || !templateIframe.contentDocument) {
                alert('Brak dokumentu do zapisu!');
                return;
            }

            const doc = templateIframe.contentDocument;

            // Krytyczne: Zsynchronizuj wartości inputów z atrybutami, aby zachowały się w HTML
            doc.querySelectorAll('input, textarea, select').forEach(el => {
                if (el.tagName === 'INPUT' && (el.type === 'checkbox' || el.type === 'radio')) {
                    if (el.checked) el.setAttribute('checked', 'checked');
                    else el.removeAttribute('checked');
                } else if (el.tagName === 'SELECT') {
                    Array.from(el.options).forEach(opt => {
                        if (opt.selected) opt.setAttribute('selected', 'selected');
                        else opt.removeAttribute('selected');
                    });
                } else {
                    el.setAttribute('value', el.value);
                }
            });

            const htmlContent = doc.documentElement.outerHTML;
            const filename = (templateSelect.options[templateSelect.selectedIndex]?.text || 'dokument') + '.html';

            try {
                advBtnSaveToLibrary.disabled = true;
                advBtnSaveToLibrary.textContent = 'Zapisywanie...';

                const response = await fetch('/api/library/save', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        content: htmlContent,
                        filename: filename
                    })
                });

                const result = await response.json();
                if (result.success) {
                    alert('✅ Dokument zapisany w bibliotece!');
                    if (typeof loadLibrary === 'function') loadLibrary(); // Odśwież widok biblioteki jeśli funkcja dostępna
                } else {
                    alert('❌ Błąd zapisu: ' + result.error);
                }
            } catch (e) {
                console.error('Save to library error:', e);
                alert('❌ Błąd połączenia z serwerem');
            } finally {
                advBtnSaveToLibrary.disabled = false;
                advBtnSaveToLibrary.textContent = 'Zapisz w bibliotece';
            }
        });
    }
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
    if (pozewFileInput) pozewFileInput.value = '';
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

        const modelSelect = document.getElementById('modelSelect');
        if (modelSelect) formData.append('model', modelSelect.value);

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

// === KRS UPLOAD FOR POZEW ===
const krsUploadZone = document.getElementById('krsUploadZone');
const krsFileInput = document.getElementById('krsFileInput');
const krsFileList = document.getElementById('krsFileList');
const btnGeneratePozew = document.getElementById('btnGeneratePozew');

let krsUploadedFiles = [];

if (krsUploadZone) {
    krsUploadZone.addEventListener('click', () => krsFileInput?.click());
    krsUploadZone.addEventListener('dragover', e => { e.preventDefault(); krsUploadZone.classList.add('dragover'); });
    krsUploadZone.addEventListener('dragleave', () => krsUploadZone.classList.remove('dragover'));
    krsUploadZone.addEventListener('drop', e => {
        e.preventDefault();
        krsUploadZone.classList.remove('dragover');
        handleKrsFiles(e.dataTransfer.files);
    });
}

if (krsFileInput) {
    krsFileInput.addEventListener('change', e => handleKrsFiles(e.target.files));
}

function handleKrsFiles(files) {
    krsUploadedFiles = [...krsUploadedFiles, ...Array.from(files)];
    renderKrsFileList();
    updateGeneratePozewButton();
    if (krsFileInput) krsFileInput.value = '';
}

function renderKrsFileList() {
    if (!krsFileList) return;
    krsFileList.innerHTML = krsUploadedFiles.map((f, i) => `
        <div class="file-item">
            <span class="file-name">${f.name}</span>
            <button class="file-remove" onclick="removeKrsFile(${i})">✕</button>
        </div>
    `).join('');
}

window.removeKrsFile = function (index) {
    krsUploadedFiles.splice(index, 1);
    renderKrsFileList();
    updateGeneratePozewButton();
};

function updateGeneratePozewButton() {
    if (btnGeneratePozew) {
        // Musi mieć KRS i źródło wezwania (zapisane lub upload)
        const hasKrs = krsUploadedFiles.length > 0;
        const hasSavedWezwania = document.querySelectorAll('#advWezwaniaList input:checked').length > 0;
        const hasUploadWezwania = pozewUploadedFiles.length > 0;
        btnGeneratePozew.disabled = !hasKrs || (!hasSavedWezwania && !hasUploadWezwania);
    }
}

// Update na zmiany checkboxów wezwań
document.addEventListener('change', e => {
    if (e.target.closest('#advWezwaniaList')) updateGeneratePozewButton();
});

// === GENERATE POZEW - FULL WORKFLOW ===
if (btnGeneratePozew) {
    btnGeneratePozew.addEventListener('click', async () => {
        const btnIcon = document.getElementById('btnGeneratePozewIcon');
        const btnText = document.getElementById('btnGeneratePozewText');
        const progressBar = document.getElementById('pozewProgressBar');
        const progressFill = document.getElementById('pozewProgressFill');
        const statusText = document.getElementById('pozewStatusText');

        btnGeneratePozew.disabled = true;
        if (btnIcon) btnIcon.innerHTML = '<span class="spinner">⏳</span>';
        if (btnText) btnText.textContent = 'Generowanie...';
        if (progressBar) progressBar.classList.remove('hidden');
        if (statusText) { statusText.classList.remove('hidden'); statusText.textContent = '🔄 Rozpoczynam...'; }
        if (progressFill) progressFill.style.width = '5%';

        try {
            let wezwanieData = null;
            let wezwanieCreatedAt = null;

            // KROK 1: Pobierz dane wezwania
            const usingSaved = !document.getElementById('pozewUploadSection')?.classList.contains('hidden') === false;

            if (pozewUploadedFiles.length > 0) {
                // OCR wezwania z pliku
                if (statusText) statusText.textContent = '📷 OCR wezwania do zapłaty...';
                if (progressFill) progressFill.style.width = '15%';

                const wezForm = new FormData();
                pozewUploadedFiles.forEach(f => wezForm.append('files', f));
                wezForm.append('template', templateSelect.value);

                const modelSelect = document.getElementById('modelSelect');
                if (modelSelect) wezForm.append('model', modelSelect.value);

                const wezResp = await fetch('/api/process_ocr', { method: 'POST', body: wezForm });
                const wezData = await wezResp.json();

                if (wezData.success && wezData.documents?.length > 0) {
                    wezwanieData = wezData.documents[0].fields;
                }
            } else {
                // Z zapisanych wezwań
                const selectedIds = Array.from(document.querySelectorAll('#advWezwaniaList input:checked')).map(cb => cb.value);
                if (selectedIds.length > 0) {
                    if (statusText) statusText.textContent = '📋 Ładowanie zapisanego wezwania...';
                    const resp = await fetch(`/api/wezwania/${selectedIds[0]}`);
                    const data = await resp.json();
                    wezwanieData = data.fields || {};
                    wezwanieCreatedAt = data.created_at || null;
                }
            }

            if (progressFill) progressFill.style.width = '30%';

            // KROK 2: Wyciągnij tekst z plików KRS (bez LLM - tylko ekstrakcja tekstu)
            if (statusText) statusText.textContent = '📄 Ekstrakcja tekstu z KRS...';
            if (progressFill) progressFill.style.width = '45%';

            let krsTexts = [];
            for (const krsFile of krsUploadedFiles) {
                const krsForm = new FormData();
                krsForm.append('file', krsFile);

                try {
                    const krsResp = await fetch('/api/extract_pdf_text', { method: 'POST', body: krsForm });
                    const krsData = await krsResp.json();

                    if (krsData.success && krsData.text) {
                        krsTexts.push(krsData.text);
                        console.log(`📄 KRS ${krsData.filename}: ${krsData.text.length} znaków` +
                            (krsData.truncated ? ` (przycięto z ${krsData.original_length})` : ''));
                    } else {
                        console.warn(`⚠️ Nie udało się wyciągnąć tekstu z: ${krsFile.name}`, krsData.error);
                    }
                } catch (e) {
                    console.warn(`❌ Błąd ekstrakcji KRS: ${krsFile.name}`, e);
                }
            }

            if (progressFill) progressFill.style.width = '70%';

            // KROK 3: Wyślij dane do analizy (mapowanie wezwania + szukanie KRS)
            if (statusText) statusText.textContent = '🔍 Szukanie numeru KRS pozwanego...';

            const allData = {
                wezwanie: wezwanieData,
                krs: krsTexts
            };

            console.log('📦 Dane wysłane do LLM (wezwanie + KRS):', JSON.stringify(allData, null, 2));

            // Pokaż surowe dane
            if (extractedDataCard) extractedDataCard.classList.remove('hidden');
            if (extractedDataContent) extractedDataContent.textContent = JSON.stringify(allData, null, 2);

            if (progressFill) progressFill.style.width = '80%';

            // Wywołaj drugi LLM do analizy i mapowania
            const analyzeResp = await fetch('/api/analyze_pozew', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(allData)
            });
            const analyzeData = await analyzeResp.json();

            console.log('🤖 LLM odpowiedź (zmapowane pola pozwu):', JSON.stringify(analyzeData, null, 2));

            if (progressFill) progressFill.style.width = '95%';

            // KROK 4: Wypełnij szablon Pozew
            if (statusText) statusText.textContent = '📝 Wypełnianie szablonu pozwu...';

            if (templateIframe && templateIframe.contentDocument && analyzeData.success && analyzeData.fields) {
                const doc = templateIframe.contentDocument;
                const pozewFields = analyzeData.fields;

                // Wypełnij pola z analizy LLM
                for (let [fieldName, value] of Object.entries(pozewFields)) {
                    if (!value) continue;
                    const inputs = doc.querySelectorAll(`input[name="${fieldName}"]`);
                    inputs.forEach(inp => {
                        inp.value = value;
                        inp.style.background = '#e8f5e9';
                    });
                }

                // Wypełnij datę wezwania z created_at pliku JSON
                if (wezwanieCreatedAt) {
                    const wezwanieDate = new Date(wezwanieCreatedAt);
                    const dd = String(wezwanieDate.getDate()).padStart(2, '0');
                    const mm = String(wezwanieDate.getMonth() + 1).padStart(2, '0');
                    const yyyy = wezwanieDate.getFullYear();
                    fillInput(doc, 'wezwanie_data', `${dd}.${mm}.${yyyy} r.`);
                }

                // Dodaj do extracted data
                if (extractedDataContent) {
                    extractedDataContent.textContent = JSON.stringify({
                        raw_data: allData,
                        mapped_fields: pozewFields
                    }, null, 2);
                }
            }

            if (progressFill) progressFill.style.width = '100%';
            if (statusText) statusText.textContent = '✅ Pozew wygenerowany!';

            // Wyczyść pliki
            krsUploadedFiles = [];
            pozewUploadedFiles = [];
            renderKrsFileList();
            renderPozewFileList();

        } catch (e) {
            if (statusText) statusText.textContent = `❌ ${e.message}`;
        } finally {
            if (btnIcon) btnIcon.textContent = '⚖️';
            if (btnText) btnText.textContent = 'Generuj Pozew';
            updateGeneratePozewButton();
            setTimeout(() => progressBar?.classList.add('hidden'), 3000);
        }
    });
}



/**
 * Dynamiczne renderowanie tabeli w iframe na podstawie zaznaczonych checkboxów.
 * Obsługuje grupy netto/brutto — jeden checkbox → dwie kolumny obok siebie z nagłówkiem grupującym.
 */
function renderDynamicTable(documents) {
    if (!templateIframe || !templateIframe.contentDocument) return;
    const doc = templateIframe.contentDocument;

    const tableHeaderRow1 = doc.getElementById('tableHeaderRow1');
    const tableHeaderRow2 = doc.getElementById('tableHeaderRow2');
    const tableBodyEl = doc.getElementById('summary-table-body');
    if (!tableHeaderRow1 || !tableBodyEl) return;

    // Zbierz zaznaczone kolumny (obsługa data-columns z przecinkiem + switch netto)
    const nettoSwitch = document.getElementById('nettoSwitch');
    const nettoEnabled = !nettoSwitch || nettoSwitch.checked;
    const selectedColumns = Array.from(document.querySelectorAll('#columnToggleList input:checked'))
        .flatMap(cb => {
            const cols = (cb.dataset.columns || '').split(',').map(s => s.trim()).filter(Boolean);
            // Jeśli switch netto wyłączony i to para (netto,brutto) → tylko brutto
            if (!nettoEnabled && cols.length === 2) return [cols[1]];
            return cols;
        });

    // Definicja grup kolumn — każda group ma label i listę podkolumn (cols)
    // Grupy z 1 col → pojedyncza kolumna; grupy z 2 cols → nagłówek grupujący + Netto/Brutto
    const columnsConfig = [
        { label: 'Nr faktury',       cols: [{ id: 'numer_faktury',              sub: null,    numeric: false }] },
        { label: 'Sprzedawca',       cols: [{ id: 'sprzedawca',                sub: null,    numeric: false }] },
        { label: 'Data wystawienia', cols: [{ id: 'data_wystawienia',           sub: null,    numeric: false }] },
        { label: 'Data sprzedaży',   cols: [{ id: 'data_sprzedazy',            sub: null,    numeric: false }] },
        { label: 'Wolumen [kWh]',    cols: [{ id: 'wolumen_energii',            sub: null,    numeric: true  }] },
        { label: 'Należność',        cols: [{ id: 'naleznos_netto',             sub: 'Netto', numeric: true  },
                                            { id: 'naleznos_brutto',            sub: 'Brutto',numeric: true  }] },
        { label: 'Kwoty',            cols: [{ id: 'kwota_netto',                sub: 'Netto', numeric: true  },
                                            { id: 'kwota_brutto',               sub: 'Brutto',numeric: true  }] },
        { label: 'VAT',              cols: [{ id: 'kwota_vat',                  sub: null,    numeric: true  }] },
        { label: 'Sprzedaż energii', cols: [{ id: 'sprzedaz_cena_netto',        sub: 'Netto', numeric: true  },
                                            { id: 'sprzedaz_cena_brutto',       sub: 'Brutto',numeric: true  }] },
        { label: 'Dystrybucja',      cols: [{ id: 'dystrybucja_cena_netto',     sub: 'Netto', numeric: true  },
                                            { id: 'dystrybucja_cena_brutto',    sub: 'Brutto',numeric: true  }] },
        { label: 'Abonamentowa',     cols: [{ id: 'oplata_abonamentowa',        sub: 'Netto', numeric: true  },
                                            { id: 'oplata_abonamentowa_brutto', sub: 'Brutto',numeric: true  }] },
        { label: 'Sieciowa stała',   cols: [{ id: 'oplata_sieciowa_stala',      sub: 'Netto', numeric: true  },
                                            { id: 'oplata_sieciowa_stala_brutto',sub:'Brutto',numeric: true  }] },
        { label: 'Sieciowa zmienna', cols: [{ id: 'oplata_sieciowa_zmienna',    sub: 'Netto', numeric: true  },
                                            { id: 'oplata_sieciowa_zmienna_brutto',sub:'Brutto',numeric:true }] },
        { label: 'Jakościowa',       cols: [{ id: 'oplata_jakosciowa',           sub: 'Netto', numeric: true  },
                                            { id: 'oplata_jakosciowa_brutto',    sub: 'Brutto',numeric: true  }] },
        { label: 'OZE',              cols: [{ id: 'oplata_oze',                  sub: 'Netto', numeric: true  },
                                            { id: 'oplata_oze_brutto',           sub: 'Brutto',numeric: true  }] },
        { label: 'Kogeneracyjna',    cols: [{ id: 'oplata_kogeneracyjna',        sub: 'Netto', numeric: true  },
                                            { id: 'oplata_kogeneracyjna_brutto', sub: 'Brutto',numeric: true  }] },
        { label: 'Przejściowa',      cols: [{ id: 'oplata_przejsciowa',          sub: 'Netto', numeric: true  },
                                            { id: 'oplata_przejsciowa_brutto',   sub: 'Brutto',numeric: true  }] },
        { label: 'Mocowa',           cols: [{ id: 'oplata_mocowa',               sub: 'Netto', numeric: true  },
                                            { id: 'oplata_mocowa_brutto',        sub: 'Brutto',numeric: true  }] },
    ];

    // Aktywne grupy — group aktywna gdy co najmniej jedna jej kolumna jest w selectedColumns
    const activeGroups = columnsConfig
        .filter(g => g.cols.some(c => selectedColumns.includes(c.id)))
        .map(g => ({
            ...g,
            // activeCols = tylko te kolumny grupy które są w selectedColumns
            activeCols: g.cols.filter(c => selectedColumns.includes(c.id)),
        }));

    // Czy którakolwiek aktywna grupa ma 2 aktywne podkolumny (netto + brutto oba widoczne)?
    const hasSubHeaders = activeGroups.some(g => g.activeCols.length > 1);

    const thBase = 'px-3 py-2 text-left text-[10px] font-bold text-zinc-500 uppercase tracking-wider';

    // 1a. Wiersz 1 nagłówka (etykiety grup)
    let header1Html = '';
    activeGroups.forEach(g => {
        if (g.activeCols.length === 1) {
            header1Html += `<th class="${thBase}" ${hasSubHeaders ? 'rowspan="2"' : ''}>${g.label}</th>`;
        } else {
            header1Html += `<th class="${thBase} text-center border-l border-zinc-200" colspan="${g.activeCols.length}">${g.label}</th>`;
        }
    });
    header1Html += `<th class="${thBase} text-right" ${hasSubHeaders ? 'rowspan="2"' : ''}>Pewność</th>`;
    tableHeaderRow1.innerHTML = header1Html;

    // 1b. Wiersz 2 nagłówka (Netto / Brutto pod grupą — tylko gdy oba widoczne)
    if (tableHeaderRow2) {
        if (hasSubHeaders) {
            let header2Html = '';
            activeGroups.forEach(g => {
                if (g.activeCols.length > 1) {
                    g.activeCols.forEach(c => {
                        header2Html += `<th class="px-3 py-1 text-center text-[9px] font-semibold text-zinc-400 border-b border-zinc-200 border-l border-zinc-200">${c.sub}</th>`;
                    });
                }
            });
            tableHeaderRow2.innerHTML = header2Html;
            tableHeaderRow2.style.display = '';
        } else {
            tableHeaderRow2.innerHTML = '';
            tableHeaderRow2.style.display = 'none';
        }
    }

    // 2. Renderuj wiersze danych
    let totalBrutto = 0;

    const distToggle = document.getElementById('distributionToggle');
    if (distToggle && distToggle.checked) totalBrutto += 3500;

    let lowConfidenceCount = 0;
    let bodyHtml = '';

    documents.forEach(docData => {
        const fields = docData.fields || {};
        const isScan = !!docData.is_vision;

        const brutoVal = parseFloat(String(fields['kwota_brutto'] || 0).replace(',', '.'));
        if (!isNaN(brutoVal)) totalBrutto += brutoVal;

        const confidence = parseInt(String(fields['pewnosc_ocr_procent'] || 0).replace('%', ''));
        if (confidence < 85 || isScan) lowConfidenceCount++;

        const rowClass = isScan
            ? 'border-b border-zinc-100 last:border-b-0 bg-yellow-50 hover:bg-yellow-100 transition-colors'
            : 'border-b border-zinc-100 last:border-b-0 hover:bg-zinc-50 transition-colors';

        bodyHtml += `<tr class="${rowClass}" title="${isScan ? '⚠ Skan – wyższe ryzyko błędu OCR' : ''}">`;

        activeGroups.forEach(g => {
            g.activeCols.forEach((c, ci) => {
                let raw = fields[c.id];
                let val;
                if (raw == null || raw === '') {
                    val = '-';
                } else if (c.id === 'wolumen_energii') {
                    const n = parseFloat(String(raw).replace(',', '.'));
                    val = !isNaN(n) ? n.toLocaleString('pl-PL', { maximumFractionDigits: 0 }) : String(raw);
                } else if (c.numeric && String(raw).includes('|')) {
                    // Wiele wartości (np. opłata pojawia się 2x w fakturze) — wypisz jedną pod drugą
                    val = String(raw).split('|')
                        .map(v => v.trim())
                        .filter(v => v !== '')
                        .map(v => formatCurrencyHelper(v))
                        .join('<br>');
                } else if (c.numeric) {
                    val = formatCurrencyHelper(raw);
                } else {
                    val = String(raw);
                }
                const isMain = c.id === 'naleznos_brutto' || c.id === 'kwota_brutto';
                const borderLeft = (g.activeCols.length > 1 && ci === 0) ? 'border-l border-zinc-100' : '';
                bodyHtml += `<td class="px-3 py-3 ${borderLeft}"><div class="${isMain ? 'text-sm font-semibold text-zinc-900' : 'text-xs text-zinc-700'} ${g.activeCols.length > 1 ? 'text-center' : ''}">${val}</div></td>`;
            });
        });

        const scanBadge = isScan
            ? `<span class="inline-flex items-center rounded-full bg-yellow-100 text-yellow-700 px-2 py-0.5 text-[10px] font-bold mr-1" title="Skan">📷</span>`
            : '';
        bodyHtml += `
            <td class="px-4 py-3 text-right">
                ${scanBadge}<span class="inline-flex items-center rounded-full ${confidence < 85 ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'} px-2 py-0.5 text-[10px] font-bold">
                    ${confidence}%
                </span>
            </td>`;

        bodyHtml += `</tr>`;
    });

    tableBodyEl.innerHTML = bodyHtml;

    // 3. Aktualizacja podsumowań w nagłówku iframe
    const summaryTotalEl = doc.getElementById('summary-total-amount');
    if (summaryTotalEl) summaryTotalEl.textContent = formatCurrencyHelper(totalBrutto);

    const headerBadgeEl = doc.getElementById('summary-header-badge');
    if (headerBadgeEl) headerBadgeEl.textContent = `${documents.length} faktur • PLN`;

    const statusTextEl = doc.getElementById('summary-ocr-status-text');
    if (statusTextEl) statusTextEl.textContent = lowConfidenceCount > 0 ? `${lowConfidenceCount} wymaga uwagi` : 'Wszystkie odczyty poprawne';

    // Threshold logic
    const threshold = 50000;
    const diff = totalBrutto - threshold;
    const thresholdAlertEl = doc.getElementById('summary-threshold-alert');
    if (thresholdAlertEl) {
        if (totalBrutto > threshold) thresholdAlertEl.classList.remove('hidden');
        else thresholdAlertEl.classList.add('hidden');
    }
    const diffValueEl = doc.getElementById('summary-difference-value');
    if (diffValueEl) {
        diffValueEl.textContent = (diff >= 0 ? '+' : '') + formatCurrencyHelper(diff);
        diffValueEl.className = `mt-1 text-2xl font-semibold ${diff >= 0 ? 'text-emerald-600' : 'text-zinc-400'}`;
    }
}

function formatCurrencyHelper(v) {
    const n = parseFloat(String(v).replace(',', '.'));
    return !isNaN(n) 
        ? n.toLocaleString('pl-PL', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
        : '0,00';
}

// Globalny listener dla checkboxów i switcha netto (delegacja)
document.addEventListener('change', (e) => {
    if ((e.target.closest('#columnToggleList') || e.target.id === 'distributionToggle' || e.target.id === 'nettoSwitch') && window.lastProcessedDocuments) {
        renderDynamicTable(window.lastProcessedDocuments);
    }
});

// Animacja kciuka switcha netto
document.addEventListener('change', (e) => {
    if (e.target.id !== 'nettoSwitch') return;
    const thumb = document.getElementById('nettoSwitchThumb');
    const track = thumb && thumb.parentElement;
    if (!thumb || !track) return;
    if (e.target.checked) {
        thumb.style.transform = 'translateX(0)';
        track.style.background = 'var(--accent-emerald)';
    } else {
        thumb.style.transform = 'translateX(16px)';
        track.style.background = '#4B5563';
    }
});
