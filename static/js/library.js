// ==================== Document Library Logic ====================

document.addEventListener('DOMContentLoaded', () => {
    const navLibrary = document.getElementById('navLibrary');
    const navItems = document.querySelectorAll('.nav-item');
    const dashboardAdvanced = document.getElementById('dashboard-advanced');
    const dashboardLibrary = document.getElementById('dashboard-library');

    if (navLibrary) {
        navLibrary.addEventListener('click', (e) => {
            e.preventDefault();
            
            // UI Update: Sidebar active state
            navItems.forEach(nav => nav.classList.remove('active'));
            navLibrary.classList.add('active');

            // View Switch
            if (dashboardAdvanced) dashboardAdvanced.classList.add('hidden');
            if (dashboardLibrary) {
                dashboardLibrary.classList.remove('hidden');
                loadLibrary();
            }
        });
    }

    // Handle template clicks to return to advanced view
    const templateNavItems = document.querySelectorAll('#sidebarTemplateNav .nav-item');
    templateNavItems.forEach(item => {
        item.addEventListener('click', () => {
            if (dashboardLibrary) dashboardLibrary.classList.add('hidden');
            if (dashboardAdvanced) dashboardAdvanced.classList.remove('hidden');
            navLibrary.classList.remove('active');
        });
    });
});

async function loadLibrary() {
    const grid = document.getElementById('library-grid');
    if (!grid) return;

    try {
        const response = await fetch('/api/library');
        const files = await response.json();

        if (files.length === 0) {
            grid.innerHTML = '<div style="padding: 40px; text-align: center; color: var(--text-muted);">Brak dokumentów w bibliotece.</div>';
            return;
        }

        renderLibrary(files);
    } catch (e) {
        console.error('Error loading library:', e);
        grid.innerHTML = '<div style="padding: 40px; text-align: center; color: #ff453a;">Błąd ładowania biblioteki.</div>';
    }
}

function renderLibrary(files) {
    const grid = document.getElementById('library-grid');
    if (!grid) return;

    grid.innerHTML = files.map(file => {
        const isImage = ['.jpg', '.jpeg', '.png', '.webp', '.bmp'].includes(file.ext);
        const iconHtml = isImage 
            ? `<img src="${file.url}" alt="${file.name}" loading="lazy">`
            : `<div class="library-pdf-icon">📄</div>`;
        
        const sizeKb = (file.size / 1024).toFixed(1) + ' KB';
        const type = isImage ? 'image' : 'pdf';

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

window.openPreview = function(url, name, type) {
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

window.closeModal = function() {
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
