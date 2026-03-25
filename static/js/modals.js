/**
 * Obsługa modali w głównej aplikacji (index.html):
 * - helpModal (Pomoc)
 * - logoutModal (Wylogowanie)
 * - resetPasswordModal (Reset hasła z AJAX)
 */

function openHelpModal() {
    document.getElementById('helpModal').classList.add('active');
}

function closeHelpModal() {
    document.getElementById('helpModal').classList.remove('active');
}

function openLogoutModal() {
    document.getElementById('logoutModal').classList.add('active');
}

function closeLogoutModal() {
    document.getElementById('logoutModal').classList.remove('active');
}

function openResetPasswordModal() {
    // Reset modal state
    document.getElementById('resetModalMessage').textContent =
        'Czy na pewno chcesz zresetować hasło? Na Twój adres e-mail zostanie wysłana wiadomość z linkiem.';
    document.getElementById('resetModalButtons').style.display = 'flex';
    document.getElementById('resetConfirmBtn').disabled = false;
    document.getElementById('resetPasswordModal').classList.add('active');
}

function closeResetPasswordModal() {
    document.getElementById('resetPasswordModal').classList.remove('active');
}

async function confirmResetPassword() {
    const btn = document.getElementById('resetConfirmBtn');
    const msgEl = document.getElementById('resetModalMessage');
    btn.disabled = true;
    btn.textContent = 'Wysyłanie...';

    try {
        const resp = await fetch('/api/settings/request-password-reset', { method: 'POST' });
        const data = await resp.json();
        if (data.success) {
            msgEl.innerHTML = '✅ ' + data.message;
            document.getElementById('resetModalButtons').style.display = 'none';
            setTimeout(() => closeResetPasswordModal(), 3000);
        } else {
            msgEl.innerHTML = '❌ ' + (data.error || 'Nieznany błąd.');
            btn.disabled = false;
            btn.textContent = 'Tak, resetuj';
        }
    } catch (e) {
        msgEl.innerHTML = '❌ Błąd połączenia z serwerem.';
        btn.disabled = false;
        btn.textContent = 'Tak, resetuj';
    }
}
