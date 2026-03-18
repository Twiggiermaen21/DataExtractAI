let libSelectedFiles = new Set();
let libFullLibraryFiles = [];
let libCurrentCategory = 'all';
let libSearchQuery = '';
let libIsSelectionMode = false;

window.toggleSelectionMode = function() {
    libIsSelectionMode = !libIsSelectionMode;
    const dashboardLibrary = document.getElementById('dashboard-library');
    const trashBtn = document.getElementById('lib-toggle-trash');
    const selectionControls = document.getElementById('library-selection-controls');
    
    if (libIsSelectionMode) {
        dashboardLibrary.classList.add('selection-mode');
        if (trashBtn) trashBtn.classList.add('active');
        if (selectionControls) selectionControls.style.display = 'flex';
    } else {
        dashboardLibrary.classList.remove('selection-mode');
        if (trashBtn) trashBtn.classList.remove('active');
        if (selectionControls) selectionControls.style.display = 'none';
        
        // Clear selection when exiting mode
        libSelectedFiles.clear();
        const checkboxes = document.querySelectorAll('.library-checkbox-container input');
        checkboxes.forEach(cb => cb.checked = false);
        const items = document.querySelectorAll('.library-item');
        items.forEach(item => item.classList.remove('selected'));
        if (document.getElementById('lib-select-all')) document.getElementById('lib-select-all').checked = false;
    }
};

function initLibrary() {
    console.log("Initializing Library...");
    const navLibrary = document.getElementById('navLibrary');
    const globalSearch = document.getElementById('global-search');
    const dashboardLibrary = document.getElementById('dashboard-library');
    const selectAllCheckbox = document.getElementById('lib-select-all');

    if (navLibrary) {
        navLibrary.replaceWith(navLibrary.cloneNode(true));
        const newNavLibrary = document.getElementById('navLibrary');

        newNavLibrary.addEventListener('click', (e) => {
            if (e) e.preventDefault();
            updateHeaderTitle(newNavLibrary.title || "Biblioteka dokumentów");
            document.querySelectorAll('.nav-item').forEach(nav => nav.classList.remove('active'));
            newNavLibrary.classList.add('active');
            
            const welcome = document.getElementById('dashboard-welcome');
            const dashboardAdvanced = document.getElementById('dashboard-advanced');
            if (welcome) welcome.classList.add('hidden');
            if (dashboardAdvanced) dashboardAdvanced.classList.add('hidden');
            if (dashboardLibrary) {
                dashboardLibrary.classList.remove('hidden');
                loadLibrary();
            }
            const header = document.querySelector('.dashboard-header');
            if (header) header.classList.add('header-padded');
        });
    }

    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', (e) => {
            selectAllFiles(e.target.checked);
        });
    }

    if (globalSearch) {
        globalSearch.addEventListener('focus', () => {
            if (dashboardLibrary && dashboardLibrary.classList.contains('hidden')) {
                const navLibrary = document.getElementById('navLibrary');
                if (navLibrary) navLibrary.click();
            }
        });
        globalSearch.addEventListener('input', (e) => {
            libSearchQuery = e.target.value.toLowerCase();
            filterAndRenderLibrary();
        });
    }

    document.querySelectorAll('.lib-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.lib-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            libCurrentCategory = tab.dataset.category;
            libSelectedFiles.clear();
            updateBatchActionBar();
            filterAndRenderLibrary();
        });
    });

    const templateNavItems = document.querySelectorAll('#sidebarTemplateNav .nav-item');
    templateNavItems.forEach(item => {
        if (item.id === 'navLibrary') return;
        item.addEventListener('click', () => {
            if (dashboardLibrary) dashboardLibrary.classList.add('hidden');
            const dashboardAdvanced = document.getElementById('dashboard-advanced');
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
        libFullLibraryFiles = await response.json();
        libSelectedFiles.clear();
        updateBatchActionBar();
        filterAndRenderLibrary();
    } catch (e) {
        console.error('Error loading library:', e);
        grid.innerHTML = '<div style="padding: 40px; text-align: center; color: #ff453a;">Błąd ładowania biblioteki.</div>';
    }
}

function filterAndRenderLibrary() {
    let filtered = libFullLibraryFiles;
    if (libCurrentCategory === 'input') {
        filtered = libFullLibraryFiles.filter(f => f.url.startsWith('/input/'));
    } else if (libCurrentCategory === 'saved') {
        filtered = libFullLibraryFiles.filter(f => f.url.startsWith('/saved/'));
    }
    if (libSearchQuery) {
        filtered = filtered.filter(f => f.name.toLowerCase().includes(libSearchQuery));
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
        const isXml = file.ext.toLowerCase() === '.xml';
        const isSelected = libSelectedFiles.has(file.url);
        
        let iconHtml = '';
        if (isImage) {
            iconHtml = `<img src="${file.url}" alt="${file.name}" loading="lazy">`;
        } else if (isHtml) {
            iconHtml = `
                <div class="library-html-preview">
                    <iframe src="${file.url}" scrolling="no"></iframe>
                    <div class="iframe-overlay"></div>
                </div>`;
        } else if (isXml) {
            iconHtml = `<div class="library-pdf-icon" style="color: #007bff; font-weight: bold; font-family: monospace;">&lt;XML&gt;</div>`;
        } else {
            iconHtml = `<div class="library-pdf-icon">📄</div>`;
        }

        const sizeKb = (file.size / 1024).toFixed(1) + ' KB';
        let type = 'pdf';
        if (isImage) type = 'image';
        else if (isHtml) type = 'html';
        else if (isXml) type = 'xml';

        return `
            <div class="library-item ${isSelected ? 'selected' : ''}" data-type="${type}" data-url="${file.url}">
                <div class="library-checkbox-container" onclick="event.stopPropagation()">
                    <input type="checkbox" ${isSelected ? 'checked' : ''} onchange="toggleFileSelection('${file.url}', this.checked)">
                </div>
                <div class="library-thumbnail" onclick="openPreview('${file.url}', '${file.name}', '${type}')">
                    ${iconHtml}
                </div>
                <div class="library-info" onclick="openPreview('${file.url}', '${file.name}', '${type}')">
                    <div class="library-name" title="${file.name}">${file.name}</div>
                    <div class="library-meta">${file.ext.toUpperCase()} • ${sizeKb}</div>
                </div>
            </div>
        `;
    }).join('');
}

window.toggleFileSelection = function(url, isChecked) {
    if (isChecked) {
        libSelectedFiles.add(url);
    } else {
        libSelectedFiles.delete(url);
    }
    
    // Update item class visually
    const item = document.querySelector(`.library-item[data-url="${url}"]`);
    if (item) {
        if (isChecked) item.classList.add('selected');
        else item.classList.remove('selected');
    }
    
    updateBatchActionBar();
};

window.selectAllFiles = function(isChecked) {
    const gridItems = document.querySelectorAll('.library-item');
    gridItems.forEach(item => {
        const url = item.dataset.url;
        const checkbox = item.querySelector('input[type="checkbox"]');
        if (checkbox) {
            checkbox.checked = isChecked;
            if (isChecked) {
                libSelectedFiles.add(url);
                item.classList.add('selected');
            } else {
                libSelectedFiles.delete(url);
                item.classList.remove('selected');
            }
        }
    });
    updateBatchActionBar();
};

function updateBatchActionBar() {
    const selectedCountSpan = document.getElementById('lib-selected-count');
    const selectAllCheckbox = document.getElementById('lib-select-all');
    const deleteBtn = document.getElementById('lib-delete-btn');
    
    if (libSelectedFiles.size > 0) {
        if (selectedCountSpan) selectedCountSpan.textContent = libSelectedFiles.size;
        if (deleteBtn) deleteBtn.style.display = 'inline-flex';
        
        // Sync select all checkbox
        const currentGridItems = document.querySelectorAll('.library-item');
        const currentGridSize = currentGridItems.length;
        if (selectAllCheckbox) {
            selectAllCheckbox.checked = (libSelectedFiles.size >= currentGridSize && currentGridSize > 0);
        }
    } else {
        if (deleteBtn) deleteBtn.style.display = 'none';
        if (selectAllCheckbox) selectAllCheckbox.checked = false;
    }
}

window.deleteSelected = async function() {
    if (libSelectedFiles.size === 0) return;
    
    const count = libSelectedFiles.size;
    const confirmMsg = count === 1 
        ? "Czy na pewno chcesz usunąć wybrany dokument?" 
        : `Czy na pewno chcesz usunąć ${count} wybranych dokumentów?`;
        
    if (!confirm(confirmMsg)) return;
    
    const urls = Array.from(libSelectedFiles);
    
    try {
        const response = await fetch('/api/library/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ urls })
        });
        
        const result = await response.json();
        
        if (result.success) {
            console.log(`Successfully deleted ${result.deleted_count} files`);
            if (result.errors && result.errors.length > 0) {
                console.warn('Some files could not be deleted:', result.errors);
            }
            
            // Refresh library
            libSelectedFiles.clear();
            loadLibrary();
        } else {
            alert('Błąd podczas usuwania: ' + result.error);
        }
    } catch (e) {
        console.error('Delete error:', e);
        alert('Wystąpił błąd podczas usuwania plików.');
    }
};

window.openPreview = function (url, name, type) {
    if (libIsSelectionMode) {
        // Toggle selection instead of opening
        const checkbox = document.querySelector(`.library-item[data-url="${url}"] input[type="checkbox"]`);
        if (checkbox) {
            checkbox.checked = !checkbox.checked;
            toggleFileSelection(url, checkbox.checked);
        }
        return;
    }

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
    } else if (type === 'xml') {
        // Fetch and show formatted XML
        modalBody.innerHTML = '<div style="padding: 20px; text-align: center;">Wczytywanie...</div>';
        fetch(url)
            .then(res => res.text())
            .then(text => {
                const pre = document.createElement('pre');
                pre.className = 'library-xml-code';
                pre.textContent = text;
                modalBody.innerHTML = '';
                modalBody.appendChild(pre);
            })
            .catch(err => {
                modalBody.innerHTML = `<div style="padding: 20px; color: red;">Błąd wczytywania: ${err}</div>`;
            });
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
