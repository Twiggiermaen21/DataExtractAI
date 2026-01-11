/* static/js/modules/generator.js */

let globalOutputData = [];

export function initGenerator() {
  console.log("Inicjalizacja generatora...");

  // 1. Ładowanie danych startowych
  refreshAllData();

  // 2. Uruchomienie cyklicznego odświeżania co 5 sekund
  setInterval(() => {
    refreshAllData();
  }, 5000);

  // 3. Globalny nasłuchiwacz Live Preview
  const container = document.getElementById("dynamic-form-container");
  if (container) {
    container.addEventListener("input", (e) => {
      if (e.target.matches("input")) {
        updatePreview(e.target.name, e.target.value);
      }
    });
  }

  // 4. Eksport funkcji do window
  window.loadSelectedTemplate = loadSelectedTemplate;
  window.fillFormData = fillFormData;
  window.generateFinalDocument = generateFinalDocument;
}

// Funkcja pomocnicza do odświeżania wszystkiego
function refreshAllData() {
  loadTemplatesForSelect();
  loadOutputData();
}

// --- FUNKCJE LOGIKI ---

function loadTemplatesForSelect() {
  fetch("/api/get_templates_json")
    .then((r) => r.json())
    .then((files) => {
      const select = document.getElementById("template-select");
      if (!select) return;

      // ZAPAMIĘTAJ AKTUALNY WYBÓR
      const savedValue = select.value;

      select.innerHTML =
        '<option value="" disabled selected>-- Wybierz z listy --</option>';
      
      files.forEach((f) => {
        const opt = document.createElement("option");
        opt.value = f;
        opt.text = f.replace(".html", "").replace(/_/g, " ");
        select.appendChild(opt);
      });

      // PRZYWRÓĆ WYBÓR (jeśli nadal istnieje na liście)
      if (savedValue) {
        // Sprawdzamy, czy opcja o takiej wartości istnieje w nowej liście
        const optionExists = Array.from(select.options).some(o => o.value === savedValue);
        if (optionExists) {
            select.value = savedValue;
        }
      }
    })
    .catch((err) => console.error("Błąd ładowania listy szablonów:", err));
}

function loadOutputData() {
  // console.log("Pobieranie danych z /api/get_output_data..."); // Opcjonalnie wyłącz logi, żeby nie spamować konsoli co 5s

  fetch("/api/get_output_data")
    .then((r) => {
      if (!r.ok) throw new Error(`HTTP error! status: ${r.status}`);
      return r.json();
    })
    .then((data) => {
      globalOutputData = data;
      const select = document.getElementById("data-import-select");
      if (!select) return;

      // ZAPAMIĘTAJ AKTUALNY WYBÓR
      const savedValue = select.value;

      select.innerHTML =
        '<option value="" disabled selected>-- Wybierz dane do wstawienia --</option>';

      if (!data || data.length === 0) {
        const option = document.createElement("option");
        option.text = "(Brak plików JSON w folderze output)";
        select.appendChild(option);
        return;
      }

      data.forEach((item, index) => {
        const option = document.createElement("option");
        // Uwaga: używamy indexu jako value. Jeśli dojdą nowe pliki na początku listy, 
        // indexy się przesuną. Dla prostoty zostawiamy index, ale w przyszłości lepiej używać ID pliku.
        option.value = index;

        // --- LOGIKA NAZYWANIA REKORDU W SELECTCIE ---
        let label = `Rekord #${index + 1}`;

        if (Array.isArray(item)) {
          const firstTextBlock = item.find(
            (block) =>
              block.block_content && block.block_content.trim().length > 0
          );

          if (firstTextBlock) {
            label =
              firstTextBlock.block_content.split("\n")[0].substring(0, 40) +
              "...";
          } else {
            label = `Dokument OCR #${index + 1} (Brak tekstu)`;
          }
        }
        else if (item.filename) {
          label = item.filename;
        }

        option.text = label;
        select.appendChild(option);
      });

      // PRZYWRÓĆ WYBÓR
      if (savedValue !== "") {
         // Sprawdzamy czy ten index nadal mieści się w zakresie tablicy
         if (select.querySelector(`option[value="${savedValue}"]`)) {
             select.value = savedValue;
         }
      }
    })
    .catch((err) => {
      console.error("Błąd ładowania danych z output:", err);
      // Nie psujemy UI przy błędzie sieci (zostawiamy stary select, jeśli był)
    });
}

function loadSelectedTemplate(filename) {
  if (!filename) return;

  fetch(`/get_template_content/${filename}`)
    .then((r) => r.text())
    .then((rawHtml) => {
      // 1. Budujemy formularz (inputy)
      buildDynamicForm(rawHtml);

      // 2. Live Preview:
      const liveHtml = rawHtml.replace(
        /\{\{\s*([a-zA-Z0-9_ąęćłńóśźżĄĘĆŁŃÓŚŹŻ]+)\s*\}\}/g,
        (match, varName) => {
          return `<span data-bind="${varName}" class="placeholder-var text-gray-400 font-bold transition-colors select-all">${match}</span>`;
        }
      );

      const preview = document.getElementById("readonly-preview");
      if (preview) preview.innerHTML = liveHtml;
    })
    .catch((err) => console.error("Błąd pobierania szablonu:", err));
}

function buildDynamicForm(htmlContent) {
  const container = document.getElementById("dynamic-form-container");
  if (!container) return;
  
  // Ważne: przy odświeżaniu szablonu formularz jest budowany na nowo.
  // Jeśli chcesz zachować wpisane wartości przy zmianie szablonu, trzeba by je tu zapamiętać.
  // Ale zazwyczaj zmiana szablonu oznacza nowy start, więc czyścimy.
  container.innerHTML = "";

  const regex = /\{\{\s*([a-zA-Z0-9_ąęćłńóśźżĄĘĆŁŃÓŚŹŻ]+)\s*\}\}/g;
  const foundVariables = new Set();
  let match;

  while ((match = regex.exec(htmlContent)) !== null) {
    foundVariables.add(match[1]);
  }

  if (foundVariables.size === 0) {
    container.innerHTML =
      '<p class="text-slate-400 text-sm text-center italic mt-4">Ten szablon nie ma zmiennych.</p>';
    return;
  }

  foundVariables.forEach((varName) => {
    const labelText = varName
      .replace(/_/g, " ")
      .replace(/\b\w/g, (l) => l.toUpperCase());

    const wrapper = document.createElement("div");
    wrapper.className = "group mb-4";

    const label = document.createElement("label");
    label.className =
      "block text-xs font-bold text-slate-400 mb-1 group-focus-within:text-indigo-400 transition-colors";
    label.innerText = labelText;

    const input = document.createElement("input");
    input.type = "text";
    input.name = varName;
    input.className =
      "w-full bg-slate-900 border border-slate-600 text-white text-sm rounded-lg p-2.5 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none transition-all placeholder-slate-600";
    input.placeholder = `...`;
    input.autocomplete = "off";

    wrapper.appendChild(label);
    wrapper.appendChild(input);
    container.appendChild(wrapper);
  });
}

function updatePreview(varName, value) {
  const targets = document.querySelectorAll(`[data-bind="${varName}"]`);
  targets.forEach((el) => {
    if (value && value.trim() !== "") {
      el.textContent = value;
      el.classList.remove("text-gray-400", "placeholder-var");
      el.classList.add("text-indigo-900", "font-medium");
    } else {
      el.textContent = `{{ ${varName} }}`;
      el.classList.remove("text-indigo-900", "font-medium");
      el.classList.add("text-indigo-900");
    }
  });
}

function fillFormData(selectedIndex) {
  if (selectedIndex === "") return;

  let ocrData = globalOutputData[selectedIndex];

  // --- AKTUALIZACJA POD NOWĄ STRUKTURĘ JSON ---
  if (ocrData && !Array.isArray(ocrData)) {
    if (ocrData.parsing_res_list) {
      ocrData = ocrData.parsing_res_list;
    } else if (ocrData.blocks) {
      ocrData = ocrData.blocks;
    }
  }

  if (!Array.isArray(ocrData)) {
    console.warn("Wybrany rekord nie zawiera poprawnej listy bloków:", ocrData);
    return;
  }

  const inputs = document.querySelectorAll("#dynamic-form-container input");

  inputs.forEach((input) => {
    const varName = input.name;
    let foundValue = null;

    const previewElement = document.querySelector(
      `#readonly-preview [data-bind="${varName}"]`
    );

    let keywords = [];

    if (previewElement) {
      const keywordSource = previewElement.closest("[data-keywords]");
      if (keywordSource) {
        const keywordsString = keywordSource.getAttribute("data-keywords");
        if (keywordsString) {
          keywords = keywordsString
            .split(",")
            .map((k) => k.trim().toLowerCase());
        }
      }
    }

    if (keywords.length > 0) {
      searchLoop: for (const block of ocrData) {
        if (!block.block_content || typeof block.block_content !== "string")
          continue;

        const lines = block.block_content.split("\n");

        for (const line of lines) {
          const lowerLine = line.toLowerCase();
          const isMatch = keywords.some((k) => lowerLine.includes(k));

          if (isMatch) {
            foundValue = line.trim();
            break searchLoop;
          }
        }
      }
    } else {
      if (!Array.isArray(ocrData) && ocrData[varName]) {
        foundValue = ocrData[varName];
      }
    }

    if (foundValue) {
      input.value = foundValue;
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.classList.add("border-emerald-500", "ring-1", "ring-emerald-500");
      setTimeout(
        () =>
          input.classList.remove(
            "border-emerald-500",
            "ring-1",
            "ring-emerald-500"
          ),
        1000
      );
    } else {
      console.log(
        `Nie znaleziono dopasowania dla zmiennej: ${varName}`
      );
    }
  });
}

function generateFinalDocument() {
  const inputs = document.querySelectorAll("#dynamic-form-container input");
  const formData = {};

  inputs.forEach((input) => {
    formData[input.name] = input.value;
  });

  const templateSelect = document.getElementById("template-select");
  if (!templateSelect || !templateSelect.value) {
    alert("Wybierz szablon!");
    return;
  }

  fetch("/generate_document", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      template: templateSelect.value,
      data: formData,
    }),
  })
    .then((response) => response.json())
    .then((result) => {
      if (result.success) {
        alert("Sukces! Plik zapisano jako: " + result.filename);
        console.log("Pełna ścieżka na serwerze:", result.filepath);
      } else {
        alert("Błąd: " + (result.error || "Nieznany błąd"));
      }
    })
    .catch((err) => {
      console.error(err);
      alert("Błąd komunikacji z serwerem.");
    });
}