/**
 * Logika dokumentu: Pozew
 * - Auto-uzupełnianie miejscowości i daty (geolokalizacja)
 * - Automatyczna zamiana kwot na słowa (via /api/slownie)
 * - Logika 40 EUR rekompensaty (kurs NBP)
 * - Obliczanie opłaty sądowej
 * - Określanie właściwości sądu (rejonowy/okręgowy)
 */
document.addEventListener("DOMContentLoaded", function () {
    // === AUTO-FILL MIEJSCOWOŚĆ I DATA ===
    const inputField = document.querySelector('input[name="meta_miejscowosc_data_dokumentu"]');

    const now = new Date();
    const day = String(now.getDate()).padStart(2, '0');
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const year = now.getFullYear();
    const currentDate = `${day}.${month}.${year} r.`;

    inputField.value = `..., ${currentDate}`;

    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(async function (position) {
            const lat = position.coords.latitude;
            const lon = position.coords.longitude;
            try {
                const url = `https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${lat}&longitude=${lon}&localityLanguage=pl`;
                const response = await fetch(url);
                const data = await response.json();
                const city = data.city || data.locality || data.principalSubdivision || "Miejscowość";
                inputField.value = `${city}, ${currentDate}`;
            } catch (error) {
                inputField.value = `${currentDate}`;
            }
        }, function (error) {
            inputField.value = `${currentDate}`;
        });
    } else {
        inputField.value = `${currentDate}`;
    }

    // === AUTOMATYCZNA ZAMIANA KWOT NA SŁOWA ===
    const mapAmountToWords = [
        { source: 'platnosc_kwota_glowna', target: 'finanse_wps_slownie' },
        { source: 'roszczenie_kwota_glowna', target: 'roszczenie_kwota_slownie' }
    ];

    mapAmountToWords.forEach(pair => {
        const sourceInputs = document.querySelectorAll(`input[name="${pair.source}"]`);
        const targetInput = document.querySelector(`input[name="${pair.target}"]`);

        sourceInputs.forEach(sourceInput => {
            if (sourceInput && targetInput) {
                let lastValue = '';

                const convertToWords = async function () {
                    const amount = sourceInput.value;
                    if (!amount || amount.trim() === '' || amount === lastValue) return;
                    lastValue = amount;

                    try {
                        const safeAmount = amount.replace(/\s*z[łl]?$/i, '').replace(/[^\d,.\s]/g, '').trim();
                        if (!safeAmount || isNaN(parseFloat(safeAmount.replace(',', '.')))) return;

                        const response = await fetch(`/api/slownie/${encodeURIComponent(safeAmount)}`);
                        const data = await response.json();

                        if (data.slownie) {
                            targetInput.value = data.slownie;
                            targetInput.style.background = '#e8f5e9';
                        }
                    } catch (error) {
                        console.error('Błąd konwersji kwoty:', error);
                    }
                };

                sourceInput.addEventListener('change', convertToWords);
                sourceInput.addEventListener('input', convertToWords);
                setInterval(convertToWords, 500);
            }
        });
    });

    // === 40 EUR COMPENSATION LOGIC ===
    const add40EurCheckbox = document.getElementById('add40EurCheckbox');
    const euroInfo = document.getElementById('euroInfo');
    const mainAmountInput = document.querySelector('input[name="platnosc_kwota_glowna"]');

    let baseAmount = 0;
    let currentEuroRate = 0;
    let compensationPLN = 0;

    if (add40EurCheckbox && mainAmountInput) {
        add40EurCheckbox.addEventListener('change', async function () {
            let currentVal = mainAmountInput.value.replace(' zł', '').replace(/\s/g, '').replace(',', '.');
            let val = parseFloat(currentVal);
            if (isNaN(val)) val = 0;

            if (this.checked) {
                try {
                    euroInfo.style.display = 'block';
                    euroInfo.textContent = 'Pobieranie kursu NBP...';

                    const response = await fetch("https://api.nbp.pl/api/exchangerates/rates/a/eur/?format=json");
                    const data = await response.json();

                    const rate = data.rates[0].mid;
                    const date = data.rates[0].effectiveDate;

                    currentEuroRate = rate;
                    compensationPLN = parseFloat((40 * rate).toFixed(2));

                    euroInfo.innerHTML = `
                        <strong>+ 40 EUR</strong> (${compensationPLN.toFixed(2).replace('.', ',')} zł) <br>
                        wg średniego kursu NBP z dnia ${date} (1 EUR = ${rate} zł)
                    `;

                    const newVal = val + compensationPLN;
                    mainAmountInput.value = newVal.toFixed(2).replace('.', ',');
                    mainAmountInput.dispatchEvent(new Event('change'));

                } catch (error) {
                    console.error("Błąd NBP:", error);
                    euroInfo.textContent = 'Błąd pobierania kursu NBP.';
                    this.checked = false;
                }
            } else {
                if (compensationPLN > 0) {
                    const newVal = Math.max(0, val - compensationPLN);
                    mainAmountInput.value = newVal.toFixed(2).replace('.', ',');
                    mainAmountInput.dispatchEvent(new Event('change'));
                }

                euroInfo.style.display = 'none';
                compensationPLN = 0;
            }
        });
    }

    // === OBLICZANIE OPŁATY SĄDOWEJ ===
    function oblicz_oplate_sadowa(wartosc_sporu) {
        if (wartosc_sporu < 0) return 0;

        if (wartosc_sporu <= 500) return 30;
        else if (wartosc_sporu <= 1500) return 100;
        else if (wartosc_sporu <= 4000) return 200;
        else if (wartosc_sporu <= 7500) return 400;
        else if (wartosc_sporu <= 10000) return 500;
        else if (wartosc_sporu <= 15000) return 750;
        else if (wartosc_sporu <= 20000) return 1000;
        else {
            let oplata = wartosc_sporu * 0.05;
            if (oplata > 100000) return 100000;
            return Math.round(oplata * 100) / 100;
        }
    }

    const courtFeeInput = document.getElementById('courtFeeInput');
    const wpsInput = document.querySelector('input[name="platnosc_kwota_glowna"]');

    if (courtFeeInput && wpsInput) {
        // === ZAOKRĄGLANIE WPS DO PEŁNEJ LICZBY ===
        wpsInput.addEventListener('blur', function () {
            let rawVal = this.value.replace(' zł', '').replace(/\s/g, '').replace(',', '.');
            let val = parseFloat(rawVal);
            if (isNaN(val) || val === 0) return;

            let rounded = Math.ceil(val);
            this.value = rounded;
            this.dispatchEvent(new Event('change'));
        });

        const updateCourtFee = () => {
            let rawVal = wpsInput.value.replace(' zł', '').replace(/\s/g, '').replace(',', '.');
            let val = parseFloat(rawVal);
            if (isNaN(val)) val = 0;

            const fee = oblicz_oplate_sadowa(val);
            let feeStr = fee.toString();
            feeStr = feeStr.replace('.', ',');
            courtFeeInput.value = feeStr + ' zł';
        };

        wpsInput.addEventListener('input', updateCourtFee);
        wpsInput.addEventListener('change', updateCourtFee);
        setInterval(updateCourtFee, 500);
        updateCourtFee();
    }

    // === LOGIKA WŁAŚCIWOŚCI SĄDU (WPS) ===
    const courtTypeSpan = document.getElementById('sad_typ');

    function updateCourtType() {
        if (!wpsInput || !courtTypeSpan) return;

        let rawVal = wpsInput.value.replace(' zł', '').replace(/\s/g, '').replace(',', '.');
        let wps = parseFloat(rawVal) || 0;

        if (wps > 100000) {
            courtTypeSpan.textContent = 'Sądu Okręgowego';
            courtTypeSpan.style.color = '#1565c0';
        } else {
            courtTypeSpan.textContent = 'Sądu Rejonowego';
            courtTypeSpan.style.color = 'inherit';
        }
    }

    if (wpsInput) {
        wpsInput.addEventListener('input', updateCourtType);
        wpsInput.addEventListener('change', updateCourtType);
        updateCourtType();
    }
});
