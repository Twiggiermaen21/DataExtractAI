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
                const response = await fetch('/api/export_excel', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ files: window.lastProcessedFiles })
                });

                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = url;
                    a.download = 'raport_faktury_energia.xlsx';
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
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
