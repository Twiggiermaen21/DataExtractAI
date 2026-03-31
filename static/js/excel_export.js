// ==================== EXCEL EXPORT LOGIC ====================
document.addEventListener('DOMContentLoaded', () => {
    const btnExportExcel = document.getElementById('btnExportExcel');
    if (btnExportExcel) {
        btnExportExcel.addEventListener('click', async () => {
            if (!window.lastProcessedFiles || window.lastProcessedFiles.length === 0) {
                alert('Brak przetworzonych plików do wyeksportowania.');
                return;
            }

            btnExportExcel.disabled = true;
            const originalText = btnExportExcel.innerHTML;
            btnExportExcel.innerHTML = '<span class="spinner">⏳</span> Generowanie...';

            try {
                const _nettoSw = document.getElementById('nettoSwitch');
                const _nettoOn = !_nettoSw || _nettoSw.checked;
                const selectedColumns = Array.from(
                    document.querySelectorAll('#columnToggleList input:checked')
                ).flatMap(cb => {
                    const cols = (cb.dataset.columns || '').split(',').map(s => s.trim()).filter(Boolean);
                    if (!_nettoOn && cols.length === 2) return [cols[1]];
                    return cols;
                });

                const response = await fetch('/api/export_excel', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        files: window.lastProcessedFiles,
                        selected_columns: selectedColumns.length ? selectedColumns : null
                    })
                });

                if (response.ok) {
                    const blob = await response.blob();
                    const fileName = 'raport_faktury_energia.xlsx';
                    triggerBrowserDownload(blob, fileName);
                } else {
                    const errData = await response.json();
                    alert(errData.error || 'Błąd podczas generowania pliku Excel.');
                }
            } catch (error) {
                console.error('Export Excel Error:', error);
                alert('Wystąpił błąd podczas eksportu.');
            } finally {
                btnExportExcel.disabled = false;
                btnExportExcel.innerHTML = originalText;
            }
        });
    }
});

/**
 * Standardowy sposób pobierania pliku w przeglądarce.
 */
function triggerBrowserDownload(blob, fileName) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }, 100);
}
