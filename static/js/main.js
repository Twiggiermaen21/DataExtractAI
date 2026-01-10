import { initTabs } from './modules/ui.js';
import { initOCR } from './modules/ocr.js';
import { initTemplateEditor } from './modules/editor.js';
import { initGenerator } from './modules/generator.js';

document.addEventListener('DOMContentLoaded', () => { 
    initTabs();
    initOCR();
    initTemplateEditor();
    initGenerator();
});