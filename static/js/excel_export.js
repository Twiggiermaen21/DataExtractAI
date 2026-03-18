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
                    const fileName = 'raport_faktury_energia.xlsx';

                    // Sprawdzamy czy działamy w pywebview
                    if (window.pywebview && window.pywebview.api && window.pywebview.api.save_file) {
                        try {
                            const reader = new FileReader();
                            reader.onloadend = async () => {
                                try {
                                    const base64Data = reader.result;
                                    const result = await window.pywebview.api.save_file(base64Data, fileName);
                                    if (result.success) {
                                        console.log('File saved via pywebview:', result.path);
                                    } else if (result && result.error !== 'Cancelled') {
                                        alert('Błąd zapisu pliku: ' + (result.error || 'Nieznany błąd'));
                                    }
                                } catch (apiErr) {
                                    console.error('JS API Call Error:', apiErr);
                                    alert('Wystąpił błąd podczas komunikacji z aplikacją.');
                                }
                            };
                            reader.readAsDataURL(blob);
                        } catch (err) {
                            console.error('Pywebview Save Error:', err);
                            // Fallback do standardowej metody jeśli coś pójdzie nie tak
                            triggerBrowserDownload(blob, fileName);
                        }
                    } else {
                        // Standardowa metoda przeglądarkowa
                        triggerBrowserDownload(blob, fileName);
                    }
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
