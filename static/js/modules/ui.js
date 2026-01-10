/* static/js/modules/ui.js */

export function initTabs() {
    // Przypisujemy funkcję openTab do obiektu window, 
    // ponieważ w HTML wywołujesz ją przez onclick="openTab(...)"
    window.openTab = function(evt, tabName) {
        // 1. Ukryj wszystkie treści zakładek
        const tabContents = document.getElementsByClassName("tab-content");
        for (let i = 0; i < tabContents.length; i++) {
            tabContents[i].classList.remove("active");
            // Dodatkowo ukrywamy stylem inline dla pewności (jeśli CSS nie zadziała od razu)
            tabContents[i].style.display = "none";
        }
        
        // 2. Zresetuj styl przycisków
        const tabLinks = document.getElementsByClassName("tab-btn");
        for (let i = 0; i < tabLinks.length; i++) {
            tabLinks[i].classList.remove("active", "text-white", "border-b-2", "border-blue-500");
            tabLinks[i].classList.add("text-slate-400");
        }
        
        // 3. Pokaż wybraną zakładkę
        const selectedTab = document.getElementById(tabName);
        if (selectedTab) {
            selectedTab.classList.add("active");
            selectedTab.style.display = "block";
        }

        // 4. Aktywuj kliknięty przycisk
        if (evt && evt.currentTarget) {
            evt.currentTarget.classList.add("active", "text-white", "border-b-2", "border-blue-500");
            evt.currentTarget.classList.remove("text-slate-400");
        }
    };

    // Inicjalizacja: Kliknij pierwszą zakładkę automatycznie, jeśli żadna nie jest aktywna
    const firstBtn = document.querySelector('.tab-btn');
    if (firstBtn) {
        firstBtn.click();
    }
}

// Funkcja obsługująca checkbox "Zaznacz wszystko"
// Eksportujemy do window, bo w HTML jest onclick="toggleAll(this)"
window.toggleAll = function(source) {
    const checkboxes = document.querySelectorAll('.file-checkbox');
    checkboxes.forEach(cb => {
        cb.checked = source.checked;
    });
};