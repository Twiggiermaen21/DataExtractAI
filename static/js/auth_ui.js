/**
 * Obsługa UI dla "Konta" i "Ustawień" oraz nawigacji do logowania/rejestracji.
 * (Wersja UI-only, bez backendu)
 */

document.addEventListener('DOMContentLoaded', () => {
    const navSettings = document.getElementById('navSettings');
    const navAccount = document.getElementById('navAccount');
    const sidebarLogo = document.getElementById('sidebar-logo');

    // Kliknięcie w logo -> powrót do Welcome
    // if (sidebarLogo) {
    //     sidebarLogo.addEventListener('click', () => {
    //         if (typeof switchView === 'function') {
    //             switchView('dashboard-welcome', 'Witaj');
    //         }
    //     });
    // }

    // Widok ustawień
    if (navSettings) {
        navSettings.addEventListener('click', (e) => {
            e.preventDefault();
            if (typeof switchView === 'function') {
                switchView('dashboard-settings', 'Ustawienia');
            }
        });
    }

    // Widok konta (tymczasowo przekierowuje do logowania)
    if (navAccount) {
        navAccount.addEventListener('click', (e) => {
            e.preventDefault();
            // W tej wersji pokazujemy alert lub przekierowujemy na stronę logowania
            const choice = confirm("To jest wersja demonstracyjna UI. Czy chcesz przejść do strony logowania?");
            if (choice) {
                window.location.href = '/login';
            }
        });
    }

    // Obsługa przycisków wewnątrz Ustawień
    const saveSettingsBtns = document.querySelectorAll('#dashboard-settings .btn-emerald');
    saveSettingsBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            btn.textContent = 'Zapisano!';
            btn.style.background = 'var(--accent-purple)';
            setTimeout(() => {
                btn.textContent = 'Zapisz ustawienia';
                btn.style.background = '';
            }, 2000);
        });
    });
});
