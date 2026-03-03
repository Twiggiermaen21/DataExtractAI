// ==================== OCR ====================

const uploadZone = document.getElementById('uploadZone');
const fileInput = document.getElementById('fileInput');
const fileList = document.getElementById('fileList');
const btnOcr = document.getElementById('btnOcr');
const btnIcon = document.getElementById('btnIcon');
const btnText = document.getElementById('btnText');
const progressBar = document.getElementById('progressBar');
const progressFill = document.getElementById('progressFill');
const statusText = document.getElementById('statusText');
const resultsCard = document.getElementById('resultsCard');
const resultsList = document.getElementById('resultsList');

let selectedFiles = [];

if (uploadZone) {
    uploadZone.addEventListener('click', () => fileInput.click());

    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });

    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('dragover');
    });

    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });
}

if (fileInput) {
    fileInput.addEventListener('change', (e) => handleFiles(e.target.files));
}


function handleFiles(files) {
    for (const file of files) {
        if (!selectedFiles.find(f => f.name === file.name)) {
            selectedFiles.push(file);
        }
    }
    renderFileList();
    updateOcrButton();
}

function renderFileList() {
    if (!fileList) return;
    fileList.innerHTML = selectedFiles.map((file, index) => `
    <div class="file-item">
      <span class="icon">📄</span>
      <span class="name">${file.name}</span>
      <span class="size">${formatSize(file.size)}</span>
      <span class="remove" onclick="removeFile(${index})">✕</span>
    </div>
  `).join('');
}

function removeFile(index) {
    selectedFiles.splice(index, 1);
    renderFileList();
    updateOcrButton();
}

function updateOcrButton() {
    if (!btnOcr) return;
    btnOcr.disabled = selectedFiles.length === 0;
}

if (btnOcr) {
    btnOcr.addEventListener('click', async () => {
        if (selectedFiles.length === 0) return;

        btnOcr.disabled = true;
        btnOcr.classList.add('loading');
        if (btnIcon) btnIcon.innerHTML = '<span class="spinner">⏳</span>';
        if (btnText) btnText.textContent = 'Przetwarzanie...';
        if (progressBar) progressBar.classList.remove('hidden');
        if (statusText) {
            statusText.classList.remove('hidden');
            statusText.textContent = 'Ładowanie modelu OCR...';
        }
        if (progressFill) progressFill.style.width = '10%';
        if (resultsCard) resultsCard.classList.add('hidden');

        const formData = new FormData();

        selectedFiles.forEach(file => {
            formData.append('files', file);
        });

        const modelSelect = document.getElementById('modelSelect');
        if (modelSelect) {
            formData.append('model', modelSelect.value);
        }

        try {
            if (statusText) statusText.textContent = 'Przetwarzanie obrazów...';
            if (progressFill) progressFill.style.width = '30%';

            const response = await fetch('/api/process_ocr', {
                method: 'POST',
                body: formData
            });

            if (progressFill) progressFill.style.width = '90%';
            const data = await response.json();
            if (progressFill) progressFill.style.width = '100%';

            if (data.success) {
                if (statusText) statusText.textContent = `✅ Przetworzono ${data.processed.length} plików`;
                showResults(data);
            } else {
                if (statusText) statusText.textContent = `❌ ${data.error}`;
            }

        } catch (error) {
            if (statusText) statusText.textContent = `❌ ${error.message}`;
        } finally {
            btnOcr.classList.remove('loading');
            if (btnIcon) btnIcon.textContent = '🚀';
            if (btnText) btnText.textContent = 'Uruchom OCR';
            btnOcr.disabled = false;

            setTimeout(() => {
                if (progressBar) progressBar.classList.add('hidden');
            }, 2000);
        }
    });
}

function showResults(data) {
    if (!resultsCard || !resultsList) return;
    resultsCard.classList.remove('hidden');

    let html = '';
    data.processed.forEach(filename => {
        html += `
      <div class="result-item">
        <div class="filename">📄 ${filename}</div>
        <div class="status">✓ JSON zapisany w /output</div>
      </div>
    `;
    });

    data.errors.forEach(err => {
        html += `
      <div class="result-item">
        <div class="filename">📄 ${err.file}</div>
        <div class="status error">✕ ${err.error}</div>
      </div>
    `;
    });

    resultsList.innerHTML = html;
    selectedFiles = [];
    renderFileList();
    updateOcrButton();
    loadJsonFiles();
}
