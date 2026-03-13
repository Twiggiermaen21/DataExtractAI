// ==================== Document Library Logic ====================

let fullLibraryFiles = [];
let currentCategory = 'all';

function initLibrary() {
    console.log("Initializing Library...");
    const navLibrary = document.getElementById('navLibrary');
    const navItems = document.querySelectorAll('.nav-item');
    const dashboardAdvanced = document.getElementById('dashboard-advanced');
    const dashboardLibrary = document.getElementById('dashboard-library');

    if (navLibrary) {
        // Remove existing listener if any (though unlikely here)
        navLibrary.replaceWith(navLibrary.cloneNode(true));
        const newNavLibrary = document.getElementById('navLibrary');

        newNavLibrary.addEventListener('click', (e) => {
            e.preventDefault();
            console.log("Library nav clicked");

            // Update Page Title
            updateHeaderTitle(newNavLibrary.title || "Biblioteka dokumentów");

            // UI Update: Sidebar active state
            document.querySelectorAll('.nav-item').forEach(nav => nav.classList.remove('active'));
            newNavLibrary.classList.add('active');

            // View Switch
            const welcome = document.getElementById('dashboard-welcome');
            const dashboardAdvanced = document.getElementById('dashboard-advanced');
            const dashboardLibrary = document.getElementById('dashboard-library');
            
            if (welcome) welcome.classList.add('hidden');
            if (dashboardAdvanced) dashboardAdvanced.classList.add('hidden');
            if (dashboardLibrary) {
                dashboardLibrary.classList.remove('hidden');
                loadLibrary();
            }
        });
    }

    // Tab switching logic
    document.querySelectorAll('.lib-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.lib-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            currentCategory = tab.dataset.category;
            filterAndRenderLibrary();
        });
    });

    // Handle template clicks to return to advanced view
    const templateNavItems = document.querySelectorAll('#sidebarTemplateNav .nav-item');
    templateNavItems.forEach(item => {
        if (item.id === 'navLibrary') return;

        item.addEventListener('click', () => {
            if (dashboardLibrary) dashboardLibrary.classList.add('hidden');
            if (dashboardAdvanced) dashboardAdvanced.classList.remove('hidden');
            const navLib = document.getElementById('navLibrary');
            if (navLib) navLib.classList.remove('active');
        });
    });
}

// Robust initialization
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initLibrary);
} else {
    initLibrary();
}

async function loadLibrary() {
    const grid = document.getElementById('library-grid');
    if (!grid) return;

    try {
        const response = await fetch('/api/library');
        fullLibraryFiles = await response.json();

        filterAndRenderLibrary();
    } catch (e) {
        console.error('Error loading library:', e);
        grid.innerHTML = '<div style="padding: 40px; text-align: center; color: #ff453a;">Błąd ładowania biblioteki.</div>';
    }
}

function filterAndRenderLibrary() {
    let filtered = fullLibraryFiles;

    // Categorization logic based on URL structure added in main.py
    if (currentCategory === 'input') {
        filtered = fullLibraryFiles.filter(f => f.url.startsWith('/input/'));
    } else if (currentCategory === 'saved') {
        filtered = fullLibraryFiles.filter(f => f.url.startsWith('/saved/'));
    }

    renderLibrary(filtered);
}

function renderLibrary(files) {
    const grid = document.getElementById('library-grid');
    if (!grid) return;

    if (files.length === 0) {
        grid.innerHTML = '<div style="padding: 40px; text-align: center; color: var(--text-muted);">Brak dokumentów w tej kategorii.</div>';
        return;
    }

    grid.innerHTML = files.map(file => {
        const isImage = ['.jpg', '.jpeg', '.png', '.webp', '.bmp'].includes(file.ext.toLowerCase());
        const isHtml = file.ext.toLowerCase() === '.html';
        
        let iconHtml = '';
        if (isImage) {
            iconHtml = `<img src="${file.url}" alt="${file.name}" loading="lazy">`;
        } else if (isHtml) {
            iconHtml = `
                <div class="library-html-preview">
                    <iframe src="${file.url}" scrolling="no"></iframe>
                    <div class="iframe-overlay"></div>
                </div>`;
        } else {
            iconHtml = `<div class="library-pdf-icon">📄</div>`;
        }

        const sizeKb = (file.size / 1024).toFixed(1) + ' KB';
        let type = 'pdf';
        if (isImage) type = 'image';
        else if (isHtml) type = 'html';

        // Show folder label for 'all' view


        return `
            <div class="library-item" onclick="openPreview('${file.url}', '${file.name}', '${type}')">
                <div class="library-thumbnail">
                    ${iconHtml}
                </div>
                <div class="library-info">
                    <div class="library-name" title="${file.name}">${file.name}</div>
                    <div class="library-meta">${file.ext.toUpperCase()} • ${sizeKb}</div>
                </div>
            </div>
        `;
    }).join('');
}

window.openPreview = function (url, name, type) {
    const modal = document.getElementById('previewModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');

    if (!modal || !modalBody) return;

    modalTitle.textContent = name;
    modalBody.innerHTML = '';

    if (type === 'image') {
        const img = document.createElement('img');
        img.src = url;
        modalBody.appendChild(img);
    } else {
        const iframe = document.createElement('iframe');
        iframe.src = url;
        modalBody.appendChild(iframe);
    }

    modal.classList.add('active');
    document.body.style.overflow = 'hidden'; // Lock scroll
};

window.closeModal = function () {
    const modal = document.getElementById('previewModal');
    const modalBody = document.getElementById('modalBody');

    if (modal) modal.classList.remove('active');
    if (modalBody) modalBody.innerHTML = '';
    document.body.style.overflow = ''; // Unlock scroll
};

// Escape key to close modal
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
});
