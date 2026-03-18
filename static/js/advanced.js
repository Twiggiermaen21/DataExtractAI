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

        btnOcrFill.disabled = true;
        btnOcrFill.classList.add('loading');
        if (btnOcrFillIcon) btnOcrFillIcon.innerHTML = '<span class="spinner">⏳</span>';
        if (btnOcrFillText) btnOcrFillText.textContent = 'Przetwarzanie...';
        if (ocrFillProgressBar) ocrFillProgressBar.classList.remove('hidden');
        if (ocrFillProgressFill) ocrFillProgressFill.style.width = '10%';

        const formData = new FormData();
        advUploadedFiles.forEach(file => formData.append('files', file));

        const templateName = templateSelect ? templateSelect.value : '';
        if (templateName) formData.append('template', templateName);

        try {
            if (ocrFillProgressFill) ocrFillProgressFill.style.width = '30%';

            const response = await fetch('/api/process_ocr', {
                method: 'POST',
                body: formData
            });

            if (ocrFillProgressFill) ocrFillProgressFill.style.width = '80%';
            const data = await response.json();
            
            // Zachowaj listę przetworzonych plików do eksportu Excela
            if (data && data.processed) {
                window.lastProcessedFiles = data.processed;
                const btnExportExcel = document.getElementById('btnExportExcel');
                if (btnExportExcel) {
                    btnExportExcel.disabled = false;
                }
            }

            if (data.success && data.documents && data.documents.length > 0) {

                // === TRYB: Podsumowanie (wiele faktur) ===
                if (advWorkflowType === 'podsumowanie') {
                    if (ocrFillProgressFill) ocrFillProgressFill.style.width = '60%';

                    if (templateIframe && templateIframe.contentDocument) {
                        const doc = templateIframe.contentDocument;
                        
                        // 1. Podstawowe dane
                        let totalAmount = 0;
                        let lowConfidenceCount = 0;
                        const threshold = 50000;

                        // Kontenery w nowym szablonie
                        const totalAmountEl = doc.getElementById('summary-total-amount');
                        const headerBadgeEl = doc.getElementById('summary-header-badge');
                        const thresholdAlertEl = doc.getElementById('summary-threshold-alert');
                        const thresholdTextEl = doc.getElementById('summary-threshold-text');
                        const differenceValueEl = doc.getElementById('summary-difference-value');
                        const ocrStatusTextEl = doc.getElementById('summary-ocr-status-text');
                        const ocrStatusBadgeEl = doc.getElementById('summary-ocr-status-badge');
                        const tableBodyEl = doc.getElementById('summary-table-body');

                        let tableHtml = '';

                        data.documents.forEach((docData, i) => {
                            const fields = docData.fields || {};
                            
                            // Ekstrakcja kluczowych danych dla tabeli
                            const sprzedawca = fields['sprzedawca'] || 'nieznany';
                            const dataWystawienia = fields['data_wystawienia'] || '-';
                            const wolumenEnergii = fields['wolumen_energii'] || '-';
                            const kwotaNetto = fields['kwota_netto'] || 0;
                            const kwotaBrutto = fields['kwota_brutto'] || 0;
                            const kwotaVat = fields['kwota_vat'] || 0;
                            const pewnoscProcent = fields['pewnosc_ocr_procent'] !== undefined ? fields['pewnosc_ocr_procent'] : '0';
                            const komentarzOcr = fields['komentarz_ocr'] || '';
                            
                            // Przeliczanie kwoty do sumy (używamy brutto)
                            const val = parseFloat(String(kwotaBrutto).replace(',', '.'));
                            if (!isNaN(val)) totalAmount += val;

                            const formatCurrency = (v) => {
                                const n = parseFloat(String(v).replace(',', '.'));
                                return !isNaN(n) 
                                    ? n.toLocaleString('pl-PL', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' zł'
                                    : '0,00 zł';
                            };

                            // Logika pewności OCR na podstawie procentów
                            const pctValue = parseInt(String(pewnoscProcent).replace('%', ''));
                            const isLowConfidence = !isNaN(pctValue) && pctValue < 85; 
                            if (isLowConfidence) lowConfidenceCount++;

                            tableHtml += `
                                <tr class="border-b border-zinc-100 last:border-b-0 hover:bg-zinc-50/50 transition-colors">
                                    <td class="px-6 py-4">
                                        <div class="text-sm font-medium text-zinc-800">${sprzedawca}</div>
                                    </td>
                                    <td class="px-6 py-4">
                                        <div class="text-sm text-zinc-700">${dataWystawienia}</div>
                                    </td>
                                    <td class="px-6 py-4">
                                        <div class="text-sm text-zinc-700">${wolumenEnergii}</div>
                                    </td>
                                    <td class="px-6 py-4">
                                        <div class="text-sm text-zinc-700">${formatCurrency(kwotaNetto)}</div>
                                    </td>
                                    <td class="px-6 py-4">
                                        <div class="text-base font-semibold text-zinc-900">${formatCurrency(kwotaBrutto)}</div>
                                    </td>
                                    <td class="px-6 py-4">
                                        <div class="text-sm text-zinc-700">${formatCurrency(kwotaVat)}</div>
                                    </td>
                                    <td class="px-6 py-4">
                                        <div class="flex items-center gap-3">
                                            <span class="inline-flex items-center rounded-full ${isLowConfidence ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'} px-3 py-1 text-xs font-semibold whitespace-nowrap">
                                                ${pewnoscProcent}${String(pewnoscProcent).includes('%') ? '' : '%'}
                                            </span>
                                        </div>
                                    </td>
                                </tr>
                            `;
                        });

                        // 2. Aktualizacja UI
                        if (tableBodyEl) tableBodyEl.innerHTML = tableHtml;
                        if (headerBadgeEl) headerBadgeEl.textContent = `${data.documents.length} faktur • PLN`;
                        if (totalAmountEl) totalAmountEl.textContent = totalAmount.toLocaleString('pl-PL', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' zł';

                        // Threshold logic
                        const diff = totalAmount - threshold;
                        if (thresholdAlertEl) {
                            if (totalAmount > threshold) {
                                thresholdAlertEl.classList.remove('hidden');
                                if (thresholdTextEl) thresholdTextEl.textContent = `Przekroczono próg ${threshold.toLocaleString()} zł`;
                            } else {
                                thresholdAlertEl.classList.add('hidden');
                            }
                        }

                        if (differenceValueEl) {
                            const diffStr = (diff >= 0 ? '+' : '') + diff.toLocaleString('pl-PL', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' zł';
                            differenceValueEl.textContent = diffStr;
                            differenceValueEl.className = `mt-1 text-2xl font-semibold ${diff >= 0 ? 'text-emerald-600' : 'text-zinc-400'}`;
                        }

                        // OCR Status
                        if (ocrStatusTextEl) {
                            ocrStatusTextEl.textContent = lowConfidenceCount > 0 ? `${lowConfidenceCount} ${lowConfidenceCount === 1 ? 'faktura wymaga' : 'faktury wymagają'} uwagi` : 'Wszystkie odczyty poprawne';
                        }
                        if (ocrStatusBadgeEl) {
                            if (lowConfidenceCount > 0) {
                                ocrStatusBadgeEl.className = "rounded-full bg-amber-100 text-amber-700 px-3 py-1 text-xs font-semibold";
                                ocrStatusBadgeEl.textContent = "niska pewność";
                            } else {
                                ocrStatusBadgeEl.className = "rounded-full bg-emerald-100 text-emerald-700 px-3 py-1 text-xs font-semibold";
                                ocrStatusBadgeEl.textContent = "wysoka pewność";
                            }
                        }
                    }

                    // Zapisz każde wezwanie do JSON
                    if (ocrFillProgressFill) ocrFillProgressFill.style.width = '80%';
                    for (let i = 0; i < data.documents.length; i++) {
                        const fields = data.documents[i].fields || {};
                        try {
                            await fetch('/api/wezwania/save', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ fields })
                            });
                        } catch (e) {
                            console.warn('Błąd zapisu wezwania JSON:', e);
                        }
                    }

                    if (ocrFillProgressFill) ocrFillProgressFill.style.width = '100%';

                    // Pokaż wyekstrahowane dane
                    if (extractedDataCard && extractedDataContent) {
                        extractedDataCard.classList.remove('hidden');
                        extractedDataContent.textContent = JSON.stringify({
                            dokumenty: data.documents.length,
                            wszystkie_dane: data.documents
                        }, null, 2);
                    }

                    advUploadedFiles = [];
                    renderAdvFileList();
                    updateAdvOcrButton();

                } else {
                    // === TRYB NORMALNY: Agregacja danych dla wezwania ===
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
                }

            } else {
                console.error('OCR Error:', data.error);
            }

            // Pokaż kartę akcji po zakończeniu przetwarzania (chyba że już jest widoczna)
            if (advActionsCard) {
                advActionsCard.classList.remove('hidden');
            }

        } catch (error) {
            console.error('Fetch Error:', error);
        } finally {
            btnOcrFill.classList.remove('loading');
            if (btnOcrFillIcon) btnOcrFillIcon.textContent = '🚀';
            if (btnOcrFillText) btnOcrFillText.textContent = 'OCR + Uzupełnij szablon';
            updateAdvOcrButton();

            setTimeout(() => {
                if (ocrFillProgressBar) ocrFillProgressBar.classList.add('hidden');
            }, 3000);
        }
    });
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
                btnPrint.disabled = false;
                btnPrint.onclick = function () {
                    if (templateIframe && templateIframe.contentWindow) {
                        templateIframe.contentWindow.focus();
                        templateIframe.contentWindow.print();
                    }
                };
            }

            const btnSaveLib = document.getElementById('advBtnSaveToLibrary');
            if (btnSaveLib) btnSaveLib.disabled = false;

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


