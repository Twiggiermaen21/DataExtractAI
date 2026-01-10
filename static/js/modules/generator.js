/* static/js/modules/generator.js */

let globalOutputData = [];

export function initGenerator() {
  console.log("Inicjalizacja generatora...");

  // 1. Ładowanie danych startowych
  loadTemplatesForSelect();
  loadOutputData();

  // 2. Globalny nasłuchiwacz Live Preview
  const container = document.getElementById("dynamic-form-container");
  if (container) {
    container.addEventListener("input", (e) => {
      if (e.target.matches("input")) {
        updatePreview(e.target.name, e.target.value);
      }
    });
  }

  // 3. Eksport funkcji do window
  window.loadSelectedTemplate = loadSelectedTemplate;
  window.fillFormData = fillFormData;
  window.generateFinalDocument = generateFinalDocument;
}

// --- FUNKCJE LOGIKI ---

function loadTemplatesForSelect() {
  fetch("/api/get_templates_json")
    .then((r) => r.json())
    .then((files) => {
      const select = document.getElementById("template-select");
      if (!select) return;
      select.innerHTML =
        '<option value="" disabled selected>-- Wybierz z listy --</option>';
      files.forEach((f) => {
        const opt = document.createElement("option");
        opt.value = f;
        opt.text = f.replace(".html", "").replace(/_/g, " ");
        select.appendChild(opt);
      });
    })
    .catch((err) => console.error("Błąd ładowania listy szablonów:", err));
}

function loadOutputData() {
  console.log("Pobieranie danych z /api/get_output_data...");

  fetch("/api/get_output_data")
    .then((r) => {
      if (!r.ok) throw new Error(`HTTP error! status: ${r.status}`);
      return r.json();
    })
    .then((data) => {
      console.log("Otrzymano dane:", data); // Zobacz w konsoli przeglądarki (F12) co przyszło

      globalOutputData = data;
      const select = document.getElementById("data-import-select");
      if (!select) return;

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
        option.value = index;

        // --- LOGIKA NAZYWANIA REKORDU W SELECTCIE ---
        let label = `Rekord #${index + 1}`;

        // Twój JSON to tablica bloków. Musimy poszukać czegoś sensownego do wyświetlenia.
        if (Array.isArray(item)) {
          // Próbujemy znaleźć blok z tekstem "Nabywca" lub "Sprzedawca" lub po prostu pierwszy tekst
          const firstTextBlock = item.find(
            (block) =>
              block.block_content && block.block_content.trim().length > 0
          );

          if (firstTextBlock) {
            // Bierzemy pierwsze 30 znaków z pierwszego bloku tekstu
            label =
              firstTextBlock.block_content.split("\n")[0].substring(0, 40) +
              "...";
          } else {
            label = `Dokument OCR #${index + 1} (Brak tekstu)`;
          }
        }
        // Jeśli to obiekt (nie tablica)
        else if (item.filename) {
          label = item.filename;
        }

        option.text = label;
        select.appendChild(option);
      });
    })
    .catch((err) => {
      console.error("Błąd ładowania danych z output:", err);
      const select = document.getElementById("data-import-select");
      if (select)
        select.innerHTML = "<option>Błąd połączenia z serwerem</option>";
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
      // Zamieniamy {{ zmienna }} na <span data-bind="zmienna">...</span>
      // Dzięki temu zachowujemy otaczające tagi HTML (gdzie mogą być data-keywords)
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

/**
 * NOWA IMPLEMENTACJA: Szuka w blokach OCR na podstawie data-keywords
 */
function fillFormData(selectedIndex) {
  if (selectedIndex === "") return;

  let ocrData = globalOutputData[selectedIndex];

  // --- AKTUALIZACJA POD NOWĄ STRUKTURĘ JSON ---
  // Sprawdzamy, czy dane są opakowane w obiekt i wyciągamy właściwą tablicę
  if (ocrData && !Array.isArray(ocrData)) {
    if (ocrData.parsing_res_list) {
      // Jeśli Python wysłał "parsing_res_list"
      ocrData = ocrData.parsing_res_list;
    } else if (ocrData.blocks) {
      // Wsparcie dla starszej wersji (opcjonalnie)
      ocrData = ocrData.blocks;
    }
  }

  // Jeśli po wyciągnięciu to nadal nie jest tablica, przerywamy
  if (!Array.isArray(ocrData)) {
    console.warn("Wybrany rekord nie zawiera poprawnej listy bloków:", ocrData);
    return;
  }

  const inputs = document.querySelectorAll("#dynamic-form-container input");

  inputs.forEach((input) => {
    const varName = input.name;
    let foundValue = null;

    // 2. Znajdź element w podglądzie, aby odczytać data-keywords
    // Szukamy elementu z data-bind="varName"
    const previewElement = document.querySelector(
      `#readonly-preview [data-bind="${varName}"]`
    );

    let keywords = [];

    if (previewElement) {
      // Sprawdzamy czy atrybut jest bezpośrednio na elemencie LUB na jego rodzicu (najczęstszy przypadek przy zagnieżdżaniu {{ }})
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

    // 3. Logika wyszukiwania w OCR (JSON)
    if (keywords.length > 0) {
      // A. Jeśli zdefiniowano słowa kluczowe -> szukamy w treści bloków
      searchLoop: for (const block of ocrData) {
        // Pomijamy puste bloki lub te bez tekstu
        if (!block.block_content || typeof block.block_content !== "string")
          continue;

        // Dzielimy na linie, żeby wyciągnąć precyzyjną wartość (np. sam numer konta)
        const lines = block.block_content.split("\n");

        for (const line of lines) {
          const lowerLine = line.toLowerCase();
          // Sprawdzamy czy linia zawiera którekolwiek słowo kluczowe
          const isMatch = keywords.some((k) => lowerLine.includes(k));

          if (isMatch) {
            foundValue = line.trim();
            break searchLoop; // Znaleziono - koniec szukania dla tego inputa
          }
        }
      }
    } else {
      // B. Fallback: Jeśli brak keywords, szukamy po nazwie zmiennej (proste dopasowanie klucza w JSON - rzadkie przy OCR blokowym, ale warto mieć)
      // Ta część zadziała tylko jeśli JSON ma strukturę { "nazwa_zmiennej": "wartość" }, a nie listę bloków.
      if (!Array.isArray(ocrData) && ocrData[varName]) {
        foundValue = ocrData[varName];
      }
    }

    // 4. Wstawienie danych do inputa
    if (foundValue) {
      input.value = foundValue;

      // Wyzwalamy zdarzenie input, aby Live Preview się zaktualizował
      input.dispatchEvent(new Event("input", { bubbles: true }));

      // Efekt wizualny (mignięcie)
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
        `Nie znaleziono dopasowania dla zmiennej: ${varName} (keywords: ${keywords.join(
          ", "
        )})`
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
  const templateName = templateSelect.value;

  fetch("/generate_document", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      template: templateName,
      data: formData,
    }),
  })
    .then((r) => r.blob())
    .then((blob) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Dokument_${templateName.replace(".html", "")}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    })
    .catch((err) => {
      console.error(err);
      alert("Błąd generowania dokumentu.");
    });
}
