// ==================== Templates - ADVANCED MODE ====================
const templateSelect = document.getElementById('templateSelect');
const templatePreview = document.getElementById('templatePreview');
const advActionsCard = document.getElementById('advActionsCard');

const advStepSource = document.getElementById('advStepSource');
const advStepLlm = document.getElementById('advStepLlm');
const advStepUpload = document.getElementById('advStepUpload');
const advDividerStep2 = document.getElementById('advDividerStep2');
const advDividerStep3 = document.getElementById('advDividerStep3');
const podsumowanieSettings = document.getElementById('podsumowanieSettings');

const advUploadZone = document.getElementById('advUploadZone');
const advFileInput = document.getElementById('advFileInput');
const advFileList = document.getElementById('advFileList');

let templateIframe = null;
let currentTemplateFields = [];
let advWorkflowType = null; // currently supported: 'podsumowanie'
let advUploadedFiles = [];
let summaryEditingRowIndex = null;

function setPreviewPlaceholder(message, color = 'var(--text-muted)') {
    if (!templatePreview) return;
    templatePreview.innerHTML = `<div style="padding: 48px; text-align: center; color: ${color};">${message}</div>`;
}

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

if (advUploadZone) {
    advUploadZone.addEventListener('click', () => advFileInput?.click());
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
            <span class="icon">&#128196;</span>
            <span class="name">${file.name}</span>
            <span class="size">${formatSize(file.size)}</span>
            <span class="remove" onclick="removeAdvFile(${index})">&#10005;</span>
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
    if (btnOcrFill) btnOcrFill.disabled = advUploadedFiles.length === 0;
}

const btnOcrFill = document.getElementById('btnOcrFill');
if (btnOcrFill) {
    btnOcrFill.addEventListener('click', async () => {
        if (advUploadedFiles.length === 0) return;
        if (advWorkflowType !== 'podsumowanie') return;

        const btnOcrFillIcon = document.getElementById('btnOcrFillIcon');
        const btnOcrFillText = document.getElementById('btnOcrFillText');
        const ocrFillProgressBar = document.getElementById('ocrFillProgressBar');
        const ocrFillProgressFill = document.getElementById('ocrFillProgressFill');
        const ocrFillProgressText = document.getElementById('ocrFillProgressText');

        const btnExportExcel = document.getElementById('btnExportExcel');

        btnOcrFill.disabled = true;
        btnOcrFill.classList.add('loading');
        if (btnOcrFillIcon) btnOcrFillIcon.innerHTML = '<span class="spinner">&#9203;</span>';
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


        if (btnExportExcel) btnExportExcel.disabled = true;

        const allDocuments = [];
        const allProcessedFiles = [];
        const templateName = templateSelect ? templateSelect.value : '';

        try {
            const nettoSwitch = document.getElementById('nettoSwitch');
            const nettoEnabled = !nettoSwitch || nettoSwitch.checked;
            const selectedColumns = Array.from(document.querySelectorAll('#columnToggleList input:checked'))
                .flatMap(cb => {
                    const cols = (cb.dataset.columns || '').split(',').map(s => s.trim()).filter(Boolean);
                    if (!nettoEnabled && cols.length === 2) return [cols[1]];
                    return cols;
                });

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
                    const response = await fetch('/api/process_ocr', { method: 'POST', body: formData });
                    const data = await response.json();
                    if (data.success && data.documents) {
                        allDocuments.push(...data.documents);
                        if (data.processed) allProcessedFiles.push(...data.processed);
                    }
                } catch (err) {
                    console.error(`Error processing file ${file.name}:`, err);
                }

                if (ocrFillProgressFill) {
                    const percent = Math.round(((i + 1) / advUploadedFiles.length) * 100);
                    ocrFillProgressFill.style.width = `${percent}%`;
                }
            }

            summaryEditingRowIndex = null;
            window.lastProcessedDocuments = allDocuments;
            window.lastProcessedFiles = allProcessedFiles;

            if (allDocuments.length > 0) {
                renderDynamicTable(allDocuments);
            }


            if (btnExportExcel) btnExportExcel.disabled = (allDocuments.length === 0);
            if (advActionsCard) advActionsCard.classList.remove('hidden');

        } catch (error) {
            console.error('OCR Processing Error:', error);
        } finally {
            btnOcrFill.classList.remove('loading');
            if (btnOcrFillIcon) btnOcrFillIcon.innerHTML = '&#128640;';
            if (btnOcrFillText) btnOcrFillText.textContent = 'Analiza zakonczona';
        }
    });
}

// === TEMPLATE SELECTION - WORKFLOW BRANCHING ===
document.addEventListener('DOMContentLoaded', () => {
    const sidebarNav = document.getElementById('sidebarTemplateNav');
    if (sidebarNav && templateSelect) {
        const navItems = sidebarNav.querySelectorAll('.nav-item');
        navItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const templateFile = item.getAttribute('data-template');
                if (!templateFile) return;

                updateHeaderTitle(item.title);
                navItems.forEach(nav => nav.classList.remove('active'));
                item.classList.add('active');

                const welcome = document.getElementById('dashboard-welcome');
                const settings = document.getElementById('dashboard-settings');
                const advanced = document.getElementById('dashboard-advanced');
                if (welcome) welcome.classList.add('hidden');
                if (settings) settings.classList.add('hidden');
                if (advanced) advanced.classList.remove('hidden');

                const header = document.querySelector('.dashboard-header');
                if (header) header.classList.add('header-padded');

                templateSelect.value = templateFile;
                templateSelect.dispatchEvent(new Event('change'));
            });
        });
    }

    const sidebarLogo = document.getElementById('sidebar-logo');
    if (sidebarLogo) {
        sidebarLogo.addEventListener('click', () => {
            updateHeaderTitle('');
            document.querySelectorAll('.nav-item').forEach(nav => nav.classList.remove('active'));

            const welcome = document.getElementById('dashboard-welcome');
            const settings = document.getElementById('dashboard-settings');
            const advanced = document.getElementById('dashboard-advanced');
            if (welcome) welcome.classList.remove('hidden');
            if (settings) settings.classList.add('hidden');
            if (advanced) advanced.classList.add('hidden');

            const header = document.querySelector('.dashboard-header');
            if (header) header.classList.remove('header-padded');
        });
    }
});

if (templateSelect) {
    templateSelect.addEventListener('change', async function () {
        const filename = this.value;

        if (podsumowanieSettings) podsumowanieSettings.classList.add('hidden');
        if (advStepSource) advStepSource.classList.add('hidden');
        if (advStepLlm) advStepLlm.classList.add('hidden');
        if (advDividerStep2) advDividerStep2.classList.add('hidden');
        if (advDividerStep3) advDividerStep3.classList.add('hidden');
        if (advStepUpload) advStepUpload.classList.add('hidden');

        const advPreviewCard = document.getElementById('advPreviewCard');
        if (advPreviewCard) {
            advPreviewCard.classList.add('hidden');
            advPreviewCard.classList.remove('card-white', 'card-beige');
            advPreviewCard.classList.add('card-purple');
        }
        if (advActionsCard) advActionsCard.classList.add('hidden');

        if (!filename) {
            advWorkflowType = null;
            summaryEditingRowIndex = null;
            setPreviewPlaceholder('Wybierz szablon aby zobaczyc podglad');
            currentTemplateFields = [];
            return;
        }

        if (!filename.includes('podsumowanie')) {
            advWorkflowType = null;
            setPreviewPlaceholder('Ten workflow zostal usuniety.', '#ff453a');
            return;
        }

        advWorkflowType = 'podsumowanie';
        if (advDividerStep2) advDividerStep2.classList.remove('hidden');
        if (advStepUpload) advStepUpload.classList.remove('hidden');
        if (podsumowanieSettings) podsumowanieSettings.classList.remove('hidden');

        if (advPreviewCard) {
            advPreviewCard.classList.remove('hidden');
            advPreviewCard.classList.remove('card-purple');
            advPreviewCard.classList.add('card-white');
        }
        if (advActionsCard) advActionsCard.classList.remove('hidden');

        try {
            const response = await fetch(`/api/template/${filename}`);
            const data = await response.json();
            currentTemplateFields = data.fields || [];

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
                templateIframe.contentDocument.close();
            }



            const btnExportExcel = document.getElementById('btnExportExcel');
            if (btnExportExcel) btnExportExcel.disabled = true;
        } catch (e) {
            setPreviewPlaceholder('Blad ladowania szablonu', '#ff453a');
        }
    });
}

loadTemplates();

function computeValidation(fields) {
    const valid = new Set();

    // Konwertuj do groszy (int) ĹĽeby uniknÄ…Ä‡ bĹ‚Ä™dĂłw zmiennoprzecinkowych
    function gr(key) {
        const v = parseFloat(String(fields[key] ?? '').replace(',', '.'));
        return isNaN(v) ? null : Math.round(v * 100);
    }

    const kn = gr('kwota_netto');
    const kb = gr('kwota_brutto');
    const kv = gr('kwota_vat');
    const sn = gr('sprzedaz_cena_netto');
    const sb = gr('sprzedaz_cena_brutto');
    const dn = gr('dystrybucja_cena_netto');
    const db = gr('dystrybucja_cena_brutto');

    // Dla par netto/brutto opĹ‚at dopuszczamy najczÄ™stsze stawki VAT
    // i niewielkÄ… tolerancjÄ™ 1 grosza wynikajÄ…cÄ… z zaokrÄ…gleĹ„.
    function validateNettoBruttoPair(nettoKey, bruttoKey) {
        const n = gr(nettoKey);
        const b = gr(bruttoKey);
        if (n === null || b === null) return;

        const rates = [1.23, 1.08, 1.05, 1.00];
        const ok = rates.some(rate => Math.abs(Math.round(n * rate) - b) <= 1);
        if (ok) {
            valid.add(nettoKey);
            valid.add(bruttoKey);
        }
    }
    // ReguĹ‚a 1: sprzedaz_netto + dystrybucja_netto = kwota_netto
    if (kn !== null && sn !== null && dn !== null && kn === sn + dn) {
        valid.add('kwota_netto');
        valid.add('sprzedaz_cena_netto');
        valid.add('dystrybucja_cena_netto');
    }

    // ReguĹ‚a 2: sprzedaz_brutto + dystrybucja_brutto = kwota_brutto
    if (kb !== null && sb !== null && db !== null && kb === sb + db) {
        valid.add('kwota_brutto');
        valid.add('sprzedaz_cena_brutto');
        valid.add('dystrybucja_cena_brutto');
    }

    // ReguĹ‚a 3: kwota_netto + kwota_vat = kwota_brutto
    if (kn !== null && kb !== null && kv !== null && kb === kn + kv) {
        valid.add('kwota_netto');
        valid.add('kwota_brutto');
    }

    // ReguĹ‚a 4: pary opĹ‚at netto/brutto sÄ… zgodne po przeliczeniu VAT
    validateNettoBruttoPair('oplata_abonamentowa', 'oplata_abonamentowa_brutto');
    validateNettoBruttoPair('oplata_sieciowa_stala', 'oplata_sieciowa_stala_brutto');
    validateNettoBruttoPair('oplata_sieciowa_zmienna', 'oplata_sieciowa_zmienna_brutto');
    validateNettoBruttoPair('oplata_jakosciowa', 'oplata_jakosciowa_brutto');
    validateNettoBruttoPair('oplata_oze', 'oplata_oze_brutto');
    validateNettoBruttoPair('oplata_kogeneracyjna', 'oplata_kogeneracyjna_brutto');
    validateNettoBruttoPair('oplata_przejsciowa', 'oplata_przejsciowa_brutto');
    validateNettoBruttoPair('oplata_mocowa', 'oplata_mocowa_brutto');
    validateNettoBruttoPair('sprzedaz_cena_netto', 'sprzedaz_cena_brutto');
    validateNettoBruttoPair('dystrybucja_cena_netto', 'dystrybucja_cena_brutto');

    return valid;
}

/**
 * Dynamiczne renderowanie tabeli w iframe na podstawie zaznaczonych checkboxĂłw.
 * ObsĹ‚uguje grupy netto/brutto â€” jeden checkbox â†’ dwie kolumny obok siebie z nagĹ‚Ăłwkiem grupujÄ…cym.
 */
function renderDynamicTable(documents) {
    if (!templateIframe || !templateIframe.contentDocument) return;
    const doc = templateIframe.contentDocument;

    const tableHeaderRow1 = doc.getElementById('tableHeaderRow1');
    const tableHeaderRow2 = doc.getElementById('tableHeaderRow2');
    const tableBodyEl = doc.getElementById('summary-table-body');
    if (!tableHeaderRow1 || !tableBodyEl) return;

    const nettoSwitch = document.getElementById('nettoSwitch');
    const nettoEnabled = !nettoSwitch || nettoSwitch.checked;
    const selectedColumns = Array.from(document.querySelectorAll('#columnToggleList input:checked'))
        .flatMap(cb => {
            const cols = (cb.dataset.columns || '').split(',').map(s => s.trim()).filter(Boolean);
            if (!nettoEnabled && cols.length === 2) return [cols[1]];
            return cols;
        });

    const columnsConfig = [
        { label: 'Nr faktury',       cols: [{ id: 'numer_faktury',              sub: null,    numeric: false }] },
        { label: 'Sprzedawca',       cols: [{ id: 'sprzedawca',                sub: null,    numeric: false }] },
        { label: 'Data wystawienia', cols: [{ id: 'data_wystawienia',           sub: null,    numeric: false }] },
        { label: 'Data sprzedaĹĽy',   cols: [{ id: 'data_sprzedazy',            sub: null,    numeric: false }] },
        { label: 'Wolumen [kWh]',    cols: [{ id: 'wolumen_energii',            sub: null,    numeric: true  }] },
        { label: 'Razem [zĹ‚]',       cols: [{ id: 'razem',                      sub: null,    numeric: true  }] },
        { label: 'Kwoty',            cols: [{ id: 'kwota_netto',                sub: 'Netto', numeric: true  },
                                            { id: 'kwota_brutto',               sub: 'Brutto',numeric: true  }] },
        { label: 'VAT',              cols: [{ id: 'kwota_vat',                  sub: null,    numeric: true  }] },
        { label: 'SprzedaĹĽ energii', cols: [{ id: 'sprzedaz_cena_netto',        sub: 'Netto', numeric: true  },
                                            { id: 'sprzedaz_cena_brutto',       sub: 'Brutto',numeric: true  }] },
        { label: 'Dystrybucja',      cols: [{ id: 'dystrybucja_cena_netto',     sub: 'Netto', numeric: true  },
                                            { id: 'dystrybucja_cena_brutto',    sub: 'Brutto',numeric: true  }] },
        { label: 'Abonamentowa',     cols: [{ id: 'oplata_abonamentowa',        sub: 'Netto', numeric: true  },
                                            { id: 'oplata_abonamentowa_brutto', sub: 'Brutto',numeric: true  }] },
        { label: 'Sieciowa staĹ‚a',   cols: [{ id: 'oplata_sieciowa_stala',      sub: 'Netto', numeric: true  },
                                            { id: 'oplata_sieciowa_stala_brutto',sub:'Brutto',numeric: true  }] },
        { label: 'Sieciowa zmienna', cols: [{ id: 'oplata_sieciowa_zmienna',    sub: 'Netto', numeric: true  },
                                            { id: 'oplata_sieciowa_zmienna_brutto',sub:'Brutto',numeric:true }] },
        { label: 'JakoĹ›ciowa',       cols: [{ id: 'oplata_jakosciowa',           sub: 'Netto', numeric: true  },
                                            { id: 'oplata_jakosciowa_brutto',    sub: 'Brutto',numeric: true  }] },
        { label: 'OZE',              cols: [{ id: 'oplata_oze',                  sub: 'Netto', numeric: true  },
                                            { id: 'oplata_oze_brutto',           sub: 'Brutto',numeric: true  }] },
        { label: 'Kogeneracyjna',    cols: [{ id: 'oplata_kogeneracyjna',        sub: 'Netto', numeric: true  },
                                            { id: 'oplata_kogeneracyjna_brutto', sub: 'Brutto',numeric: true  }] },
        { label: 'PrzejĹ›ciowa',      cols: [{ id: 'oplata_przejsciowa',          sub: 'Netto', numeric: true  },
                                            { id: 'oplata_przejsciowa_brutto',   sub: 'Brutto',numeric: true  }] },
        { label: 'Mocowa',           cols: [{ id: 'oplata_mocowa',               sub: 'Netto', numeric: true  },
                                            { id: 'oplata_mocowa_brutto',        sub: 'Brutto',numeric: true  }] },
    ];

    const activeGroups = columnsConfig
        .filter(g => g.cols.some(c => selectedColumns.includes(c.id)))
        .map(g => ({
            ...g,
            activeCols: g.cols.filter(c => selectedColumns.includes(c.id)),
        }));

    const hasSubHeaders = activeGroups.some(g => g.activeCols.length > 1);
    const thBase = 'px-3 py-2 text-left text-[10px] font-bold text-zinc-500 uppercase tracking-wider';

    let header1Html = '';
    activeGroups.forEach(g => {
        if (g.activeCols.length === 1) {
            header1Html += `<th class="${thBase}" ${hasSubHeaders ? 'rowspan="2"' : ''}>${g.label}</th>`;
        } else {
            header1Html += `<th class="${thBase} text-center border-l border-zinc-200" colspan="${g.activeCols.length}">${g.label}</th>`;
        }
    });
    header1Html += `<th class="${thBase} text-right" ${hasSubHeaders ? 'rowspan="2"' : ''}>Skan</th>`;
    header1Html += `<th class="${thBase} text-right" ${hasSubHeaders ? 'rowspan="2"' : ''}>Akcje</th>`;
    tableHeaderRow1.innerHTML = header1Html;

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

    let totalBrutto = 0;

    const distToggle = document.getElementById('distributionToggle');
    if (distToggle && distToggle.checked) totalBrutto += 3500;

    let lowConfidenceCount = 0;
    let bodyHtml = '';

    documents.forEach((docData, rowIndex) => {
        const fields = docData.fields || {};
        const isScan = !!docData.is_vision;
        const validFields = computeValidation(fields);
        const isEditing = summaryEditingRowIndex === rowIndex;

        const brutoVal = parseFloat(String(fields['razem'] ?? fields['kwota_brutto'] ?? 0).replace(',', '.'));
        if (!isNaN(brutoVal)) totalBrutto += brutoVal;

        if (isScan) lowConfidenceCount++;

        const baseRowClass = isScan
            ? 'border-b border-zinc-100 last:border-b-0 bg-yellow-50 hover:bg-yellow-100 transition-colors'
            : 'border-b border-zinc-100 last:border-b-0 hover:bg-zinc-50 transition-colors';

        const rowClass = isEditing
            ? `${baseRowClass} bg-emerald-50/70 hover:bg-emerald-100/60`
            : baseRowClass;

        bodyHtml += `<tr class="${rowClass}" data-row-index="${rowIndex}" title="${isScan ? 'Skan - wyĹĽsze ryzyko bĹ‚Ä™du OCR' : ''}">`;

        activeGroups.forEach(g => {
            g.activeCols.forEach((c, ci) => {
                const isMain = c.id === 'naleznos_brutto' || c.id === 'kwota_brutto' || c.id === 'razem';
                const borderLeft = (g.activeCols.length > 1 && ci === 0) ? 'border-l border-zinc-100' : '';
                const validStyle = (!isEditing && validFields.has(c.id)) ? ' style="background:#d1fae5;"' : '';

                if (isEditing) {
                    const inputValue = fields[c.id] == null ? '' : String(fields[c.id]);
                    bodyHtml += `<td class="px-2 py-2 ${borderLeft}">
                        <input type="text" data-field-id="${c.id}" value="${escapeAttr(inputValue)}" class="w-full min-w-[110px] rounded-lg border border-emerald-300 bg-white px-2 py-1.5 text-xs text-zinc-800 focus:outline-none focus:ring-2 focus:ring-emerald-400" />
                    </td>`;
                } else {
                    const val = getSummaryDisplayValue(fields[c.id], c);
                    bodyHtml += `<td class="px-3 py-3 ${borderLeft}"${validStyle}><div class="${isMain ? 'text-sm font-semibold text-zinc-900' : 'text-xs text-zinc-700'} ${g.activeCols.length > 1 ? 'text-center' : ''}">${val}</div></td>`;
                }
            });
        });

        bodyHtml += `
            <td class="px-4 py-3 text-center">
                ${isScan ? `<span class="inline-flex items-center rounded-full bg-yellow-100 text-yellow-700 px-2 py-0.5 text-[10px] font-bold" title="Skan - wyĹĽsze ryzyko bĹ‚Ä™du OCR">Skan</span>` : ''}
            </td>`;

        if (isEditing) {
            bodyHtml += `
                <td class="px-4 py-3 text-right whitespace-nowrap">
                    <div class="inline-flex items-center gap-1">
                        <button type="button" data-action="save-row" data-row-index="${rowIndex}" class="rounded-lg border border-emerald-300 bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-700 hover:bg-emerald-100" title="Zapisz wiersz">Zapisz</button>
                        <button type="button" data-action="cancel-row" data-row-index="${rowIndex}" class="rounded-lg border border-zinc-300 bg-white px-2 py-1 text-xs font-semibold text-zinc-600 hover:bg-zinc-100" title="Anuluj edycjÄ™">Anuluj</button>
                    </div>
                </td>`;
        } else {
            bodyHtml += `
                <td class="px-4 py-3 text-right whitespace-nowrap">
                    <button type="button" data-action="edit-row" data-row-index="${rowIndex}" class="rounded-lg border border-zinc-300 bg-white px-2 py-1 text-xs font-semibold text-zinc-700 hover:bg-zinc-100" title="Edytuj wiersz">&#9998; Edytuj</button>
                </td>`;
        }

        bodyHtml += `</tr>`;
    });

    if (!documents || documents.length === 0) {
        const dynamicColsCount = activeGroups.reduce((sum, g) => sum + g.activeCols.length, 0);
        const totalCols = dynamicColsCount + 2;
        tableBodyEl.innerHTML = `
            <tr>
                <td colspan="${Math.max(totalCols, 1)}" class="p-8 text-center text-zinc-400 italic">
                    Brak danych do wyĹ›wietlenia.
                </td>
            </tr>`;
    } else {
        tableBodyEl.innerHTML = bodyHtml;
        bindSummaryTableActions(doc, documents);
    }

    const summaryTotalEl = doc.getElementById('summary-total-amount');
    if (summaryTotalEl) summaryTotalEl.textContent = formatCurrencyHelper(totalBrutto);

    const headerBadgeEl = doc.getElementById('summary-header-badge');
    if (headerBadgeEl) headerBadgeEl.textContent = `${documents.length} faktur â€˘ PLN`;

    const statusTextEl = doc.getElementById('summary-ocr-status-text');
    if (statusTextEl) statusTextEl.textContent = lowConfidenceCount > 0 ? `${lowConfidenceCount} wymaga uwagi` : 'Wszystkie odczyty poprawne';

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

function bindSummaryTableActions(doc, documents) {
    const tableBodyEl = doc.getElementById('summary-table-body');
    if (!tableBodyEl) return;

    tableBodyEl.querySelectorAll('button[data-action="edit-row"]').forEach(btn => {
        btn.addEventListener('click', () => {
            const rowIndex = Number(btn.dataset.rowIndex);
            if (Number.isNaN(rowIndex)) return;
            summaryEditingRowIndex = rowIndex;
            renderDynamicTable(documents);
        });
    });

    tableBodyEl.querySelectorAll('button[data-action="cancel-row"]').forEach(btn => {
        btn.addEventListener('click', () => {
            summaryEditingRowIndex = null;
            renderDynamicTable(documents);
        });
    });

    tableBodyEl.querySelectorAll('button[data-action="save-row"]').forEach(btn => {
        btn.addEventListener('click', () => {
            const rowIndex = Number(btn.dataset.rowIndex);
            if (Number.isNaN(rowIndex) || !documents[rowIndex]) return;

            const rowEl = tableBodyEl.querySelector(`tr[data-row-index="${rowIndex}"]`);
            if (!rowEl) return;

            if (!documents[rowIndex].fields || typeof documents[rowIndex].fields !== 'object') {
                documents[rowIndex].fields = {};
            }

            rowEl.querySelectorAll('input[data-field-id]').forEach(input => {
                const fieldId = input.dataset.fieldId;
                if (!fieldId) return;
                documents[rowIndex].fields[fieldId] = input.value;
            });

            summaryEditingRowIndex = null;
            window.lastProcessedDocuments = documents;
            renderDynamicTable(documents);
        });
    });
}

function getSummaryDisplayValue(rawValue, columnConfig) {
    if (rawValue == null || rawValue === '') {
        return '-';
    }

    if (columnConfig.id === 'wolumen_energii') {
        const n = parseFloat(String(rawValue).replace(',', '.'));
        return !isNaN(n) ? n.toLocaleString('pl-PL', { maximumFractionDigits: 0 }) : escapeHtml(String(rawValue));
    }

    if (columnConfig.numeric && String(rawValue).includes('|')) {
        return String(rawValue).split('|')
            .map(v => v.trim())
            .filter(v => v !== '')
            .map(v => formatCurrencyHelper(v))
            .join('<br>');
    }

    if (columnConfig.numeric) {
        return formatCurrencyHelper(rawValue);
    }

    return escapeHtml(String(rawValue));
}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function escapeAttr(value) {
    return escapeHtml(value).replace(/`/g, '&#96;');
}

function formatCurrencyHelper(v) {
    const n = parseFloat(String(v).replace(',', '.'));
    return !isNaN(n) 
        ? n.toLocaleString('pl-PL', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
        : '0,00';
}

// Globalny listener dla checkboxĂłw i switcha netto (delegacja)
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


