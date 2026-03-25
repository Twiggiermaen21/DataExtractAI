/**
 * Obsługa UI dla Ustawień konta.
 * Ładuje profil z API i obsługuje zmiany nazwy, emaila (z potwierdzeniem mailowym).
 */

document.addEventListener('DOMContentLoaded', () => {
    const navSettings = document.getElementById('navSettings');
    const navAccount = document.getElementById('navAccount');

    // ── Nawigacja do widoku ustawień ──────────────────────────────────
    if (navSettings) {
        navSettings.addEventListener('click', (e) => {
            e.preventDefault();
            if (typeof switchView === 'function') {
                switchView('dashboard-settings', 'Ustawienia');
            }
            loadProfile();
        });
    }

    if (navAccount) {
        navAccount.addEventListener('click', (e) => {
            e.preventDefault();
            if (typeof switchView === 'function') {
                switchView('dashboard-settings', 'Ustawienia');
            }
            loadProfile();
        });
    }

    // ── Przycisk Zapisz ──────────────────────────────────────────────
    const saveBtn = document.getElementById('settings-save-btn');
    if (saveBtn) {
        saveBtn.addEventListener('click', handleSaveSettings);
    }
});

// Oryginalne wartości z serwera (do porównania)
let _originalUsername = '';
let _originalEmail = '';

/**
 * Pobiera aktualny profil z API i wypełnia pola.
 */
async function loadProfile() {
    try {
        const resp = await fetch('/api/settings/profile');
        if (!resp.ok) return;
        const data = await resp.json();

        _originalUsername = data.username || '';
        _originalEmail = data.email || '';

        const usernameInput = document.getElementById('settings-username');
        const emailInput = document.getElementById('settings-email');
        if (usernameInput) usernameInput.value = _originalUsername;
        if (emailInput) emailInput.value = _originalEmail;

        hideStatus();
    } catch (e) {
        console.error('Nie udało się pobrać profilu:', e);
    }
}

/**
 * Obsługa kliknięcia "Zapisz ustawienia".
 * Sprawdza co się zmieniło i wysyła odpowiednie żądania.
 */
async function handleSaveSettings() {
    const usernameInput = document.getElementById('settings-username');
    const emailInput = document.getElementById('settings-email');
    const btn = document.getElementById('settings-save-btn');

    const newUsername = (usernameInput?.value || '').trim();
    const newEmail = (emailInput?.value || '').trim().toLowerCase();

    const nameChanged = newUsername !== _originalUsername;
    const emailChanged = newEmail !== _originalEmail.toLowerCase();

    if (!nameChanged && !emailChanged) {
        showStatus('Nic nie zostało zmienione.', 'info');
        return;
    }

    btn.disabled = true;
    btn.textContent = 'Wysyłanie...';

    const results = [];

    // Zmiana nazwy konta
    if (nameChanged) {
        try {
            const resp = await fetch('/api/settings/change-name', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ new_name: newUsername }),
            });
            const data = await resp.json();
            results.push(data.success ? `✅ ${data.message}` : `❌ Nazwa: ${data.error}`);
        } catch (e) {
            results.push('❌ Nazwa: Błąd połączenia.');
        }
    }

    // Zmiana e-mail
    if (emailChanged) {
        try {
            const resp = await fetch('/api/settings/change-email', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ new_email: newEmail }),
            });
            const data = await resp.json();
            results.push(data.success ? `✅ ${data.message}` : `❌ E-mail: ${data.error}`);
        } catch (e) {
            results.push('❌ E-mail: Błąd połączenia.');
        }
    }

    showStatus(results.join('<br>'), results.every(r => r.startsWith('✅')) ? 'success' : 'warning');

    btn.disabled = false;
    btn.textContent = 'Zapisz ustawienia';
}

/**
 * Pokazuje toast statusu w panelu ustawień.
 */
function showStatus(html, type = 'info') {
    const el = document.getElementById('settings-status');
    if (!el) return;

    const colors = {
        success: { bg: 'rgba(52, 211, 153, 0.12)', border: 'rgba(52, 211, 153, 0.3)', color: '#34d399' },
        warning: { bg: 'rgba(251, 191, 36, 0.12)', border: 'rgba(251, 191, 36, 0.3)', color: '#fbbf24' },
        error: { bg: 'rgba(248, 113, 113, 0.12)', border: 'rgba(248, 113, 113, 0.3)', color: '#f87171' },
        info: { bg: 'rgba(96, 165, 250, 0.12)', border: 'rgba(96, 165, 250, 0.3)', color: '#60a5fa' },
    };
    const c = colors[type] || colors.info;

    el.style.display = 'block';
    el.style.background = c.bg;
    el.style.border = `1px solid ${c.border}`;
    el.style.color = c.color;
    el.innerHTML = html;
}

function hideStatus() {
    const el = document.getElementById('settings-status');
    if (el) el.style.display = 'none';
}
