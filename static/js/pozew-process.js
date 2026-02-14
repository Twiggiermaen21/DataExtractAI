// ==================== POZEW - PRZETWARZANIE ====================

const btnProcessPozew = document.getElementById('btnProcessPozew');

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

                    // Data wezwania (z pola created_at)
                    if (w.created_at) {
                        const wezwanieDate = new Date(w.created_at);
                        const dd = String(wezwanieDate.getDate()).padStart(2, '0');
                        const mm = String(wezwanieDate.getMonth() + 1).padStart(2, '0');
                        const yyyy = wezwanieDate.getFullYear();
                        fillInput(doc, 'wezwanie_data', `${dd}.${mm}.${yyyy} r.`);
                    }

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

// fillInput is defined in helpers.js
