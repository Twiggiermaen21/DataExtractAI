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

function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function fillInput(doc, name, value) {
    const inputs = doc.querySelectorAll(`input[name="${name}"]`);
    inputs.forEach(input => {
        input.value = value;
        input.style.background = '#e8f5e9';
    });
}

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

// Funkcje używane w onchange z dynamicznie tworzonych elementów HTML
function getSelectedJsonFiles() {
    const checkboxes = document.querySelectorAll('#jsonCheckboxList input[type="checkbox"]:checked');
    return Array.from(checkboxes).map(cb => cb.value);
}

function updateLlmButton() {
    const btnRunLlm = document.getElementById('btnRunLlm');
    if (btnRunLlm) {
        const selected = getSelectedJsonFiles();
        btnRunLlm.disabled = selected.length === 0;
    }
}

function updateHeaderTitle(title) {
    const headerTitle = document.getElementById('header-page-title');
    if (headerTitle) {
        headerTitle.textContent = title;
    }
}
// Dodaj event listener do przełączania sidebaru
document.addEventListener('DOMContentLoaded', () => {
    const sidebarToggleBtn = document.getElementById('sidebar-toggle-btn');
    const appLayout = document.querySelector('.app-layout');

    if (sidebarToggleBtn && appLayout) {
        // Przywróć stan z localStorage
        const isExpanded = localStorage.getItem('sidebarExpanded') === 'true';
        if (isExpanded) {
            appLayout.classList.add('sidebar-expanded');
        }

        sidebarToggleBtn.addEventListener('click', () => {
            const nowExpanded = appLayout.classList.toggle('sidebar-expanded');
            localStorage.setItem('sidebarExpanded', nowExpanded);
        });
    }
});
