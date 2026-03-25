/**
 * Logika dokumentu: Wezwanie do Zapłaty
 * - Auto-uzupełnianie miejscowości i daty (geolokalizacja)
 * - Auto-korekta daty odsetek (+1 dzień)
 */
document.addEventListener("DOMContentLoaded", function () {
    // === AUTO-FILL MIEJSCOWOŚĆ I DATA ===
    const inputField = document.querySelector('#miejscowosc_data');

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
                console.error("Błąd pobierania miasta:", error);
                inputField.value = `${currentDate}`;
            }
        }, function (error) {
            console.warn("Brak zgody na lokalizację:", error);
            inputField.value = `${currentDate}`;
        });
    } else {
        inputField.value = `${currentDate}`;
    }

    // === AUTO-KOREKTA DATY ODSETEK (+1 DZIEŃ) ===
    const interestInput = document.querySelector('input[name="Znajdz_na_fakturze_date_terminu_platnosci_od_ktorej_beda_liczone_odsetki"]');

    if (interestInput) {
        interestInput.addEventListener('change', function () {
            let val = this.value.trim();
            val = val.replace(/r\.?$/i, '').trim();

            const parts = val.split('.');
            if (parts.length === 3) {
                const d = parseInt(parts[0], 10);
                const m = parseInt(parts[1], 10) - 1;
                const y = parseInt(parts[2], 10);

                if (!isNaN(d) && !isNaN(m) && !isNaN(y)) {
                    const date = new Date(y, m, d);
                    if (date.getFullYear() === y && date.getMonth() === m && date.getDate() === d) {
                        date.setDate(date.getDate() + 1);

                        const newDay = String(date.getDate()).padStart(2, '0');
                        const newMonth = String(date.getMonth() + 1).padStart(2, '0');
                        const newYear = date.getFullYear();

                        this.value = `${newDay}.${newMonth}.${newYear}`;
                    }
                }
            }
        });
    }
});
