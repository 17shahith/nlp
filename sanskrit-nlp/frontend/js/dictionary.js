/** Dictionary page: search, browse, add words, edit words, and manage pending AI suggestions. */

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

async function doSearch() {
  const q = document.getElementById("searchInput").value.trim();
  const box = document.getElementById("searchResult");
  if (!q) return;
  box.textContent = "Searching...";
  try {
    const res = await Api.lookup(q);
    box.innerHTML = "";
    const line = el("div");
    line.innerHTML =
      `<span class="devanagari" style="font-size:1.4rem">${res.matched_form || res.lemma}</span> ` +
      `&mdash; <strong>${res.english}</strong> (${res.category}` +
      (res.gender ? `, ${res.gender}` : "") +
      (res.number && res.number !== "unspecified" ? `, ${res.number}` : "") +
      (res.case ? `, ${res.case}` : "") + `)`;
    box.appendChild(line);
  } catch (err) {
    box.textContent = err.message;
  }
}

async function loadWords() {
  const category = document.getElementById("categoryFilter").value;
  const table = document.getElementById("wordsTable");
  table.innerHTML = "<tr><td>Loading...</td></tr>";
  try {
    const { items } = await Api.listWords(category || undefined);
    table.innerHTML = "";
    const thead = el("tr");
    ["Lemma", "IAST", "English", "Category", "Gender", "Sample forms", "Actions"].forEach((h) =>
      thead.appendChild(el("th", null, h))
    );
    table.appendChild(thead);
    items.forEach((w) => {
      const row = el("tr");
      row.appendChild(el("td", "devanagari", w.lemma));
      row.appendChild(el("td", null, w.iast));
      row.appendChild(el("td", null, w.english));
      row.appendChild(el("td", null, w.category));
      row.appendChild(el("td", null, w.gender || "-"));
      const sample = (w.forms || []).slice(0, 3).map((f) => f.form).join(", ");
      row.appendChild(el("td", "devanagari", sample));
      
      const actionsCell = el("td", "actions-cell");
      
      const editBtn = el("button", "secondary", "Edit");
      editBtn.addEventListener("click", () => openEditWordModal(w));
      
      const delBtn = el("button", "secondary", "Delete");
      delBtn.addEventListener("click", () => confirmDeleteWord(w.lemma));
      
      actionsCell.appendChild(editBtn);
      actionsCell.appendChild(delBtn);
      
      row.appendChild(actionsCell);
      
      table.appendChild(row);
    });
  } catch (err) {
    table.innerHTML = `<tr><td>Unable to load dictionary entries. Please try again. (${err.message})</td></tr>`;
  }
}

// Modal handling
const wordModal = document.getElementById("wordModal");
const wordForm = document.getElementById("wordForm");
const wordFormMessage = document.getElementById("wordFormMessage");
const saveWordBtn = document.getElementById("saveWordBtn");

function closeWordModal() {
  wordModal.classList.add("hidden");
}

document.getElementById("openAddWordModalBtn").addEventListener("click", () => {
  wordForm.reset();
  document.getElementById("original_lemma").value = "";
  document.getElementById("wordModalTitle").textContent = "Add New Word";
  wordFormMessage.textContent = "";
  wordFormMessage.className = "muted";
  saveWordBtn.disabled = false;
  saveWordBtn.textContent = "Save Word";
  wordModal.classList.remove("hidden");
});

function openEditWordModal(w) {
  wordForm.reset();
  document.getElementById("original_lemma").value = w.lemma;
  document.getElementById("wordModalTitle").textContent = "Edit Word";
  wordFormMessage.textContent = "";
  wordFormMessage.className = "muted";
  saveWordBtn.disabled = false;
  saveWordBtn.textContent = "Save Word";
  
  wordForm.elements["lemma"].value = w.lemma;
  wordForm.elements["iast"].value = w.iast || "";
  wordForm.elements["english"].value = w.english || "";
  wordForm.elements["category"].value = w.category || "";
  wordForm.elements["gender"].value = w.gender || "";
  wordForm.elements["person"].value = w.person || "";
  wordForm.elements["number"].value = w.number || "";
  wordForm.elements["notes"].value = w.notes || "";
  
  if (w.forms && w.forms.length > 0) {
    wordForm.elements["forms"].value = JSON.stringify(w.forms, null, 2);
  } else {
    wordForm.elements["forms"].value = "";
  }
  
  wordModal.classList.remove("hidden");
}

document.getElementById("closeWordModalBtn").addEventListener("click", closeWordModal);
document.getElementById("cancelWordModalBtn").addEventListener("click", closeWordModal);

wordForm.addEventListener("submit", async (evt) => {
  evt.preventDefault();
  const data = new FormData(wordForm);
  
  let forms = [];
  const formsText = data.get("forms");
  if (formsText && formsText.trim()) {
    try {
      forms = JSON.parse(formsText);
    } catch (e) {
      wordFormMessage.textContent = "Sample Forms must be valid JSON.";
      wordFormMessage.className = "badge fail";
      return;
    }
  }

  const payload = {
    lemma: data.get("lemma"),
    iast: data.get("iast"),
    english: data.get("english"),
    category: data.get("category"),
    gender: data.get("gender") || null,
    person: data.get("person") ? parseInt(data.get("person")) : null,
    number: data.get("number") || null,
    notes: data.get("notes") || null,
    forms,
  };

  saveWordBtn.disabled = true;
  saveWordBtn.textContent = "Saving...";
  wordFormMessage.textContent = "";
  wordFormMessage.className = "muted";

  try {
    const originalLemma = data.get("original_lemma");
    if (originalLemma) {
      await Api.updateWord(originalLemma, payload);
      wordFormMessage.textContent = "Word updated successfully.";
    } else {
      await Api.addWord(payload);
      wordFormMessage.textContent = "Word added successfully.";
    }
    wordFormMessage.className = "badge pass";
    setTimeout(() => { 
      closeWordModal(); 
      loadWords(); 
    }, 1500);
  } catch (err) {
    wordFormMessage.textContent = err.message;
    wordFormMessage.className = "badge fail";
    saveWordBtn.disabled = false;
    saveWordBtn.textContent = "Save Word";
  }
});

async function confirmDeleteWord(lemma) {
  if (confirm("Are you sure you want to delete this dictionary entry?")) {
    try {
      await Api.deleteWord(lemma);
      loadWords();
    } catch (err) {
      alert(`Error deleting word: ${err.message}`);
    }
  }
}

async function loadPending() {
  const table = document.getElementById("pendingTable");
  const empty = document.getElementById("pendingEmpty");
  try {
    const { items } = await Api.pendingWords();
    table.innerHTML = "";
    empty.textContent = "";
    if (items.length === 0) {
      empty.textContent = "No pending suggestions.";
      return;
    }
    const thead = el("tr");
    ["Lemma", "English", "Category", "Actions"].forEach((h) => thead.appendChild(el("th", null, h)));
    table.appendChild(thead);
    items.forEach((w) => {
      const row = el("tr");
      row.appendChild(el("td", "devanagari", w.lemma));
      row.appendChild(el("td", null, w.english));
      row.appendChild(el("td", null, w.category));
      const actions = el("td");
      const approveBtn = el("button", "secondary", "Approve");
      approveBtn.style.marginRight = "6px";
      approveBtn.addEventListener("click", async () => {
        await Api.approveWord(w.lemma);
        loadPending();
        loadWords();
      });
      const rejectBtn = el("button", "secondary", "Reject");
      rejectBtn.addEventListener("click", async () => {
        await Api.deleteWord(w.lemma);
        loadPending();
      });
      actions.appendChild(approveBtn);
      actions.appendChild(rejectBtn);
      row.appendChild(actions);
      table.appendChild(row);
    });
  } catch (err) {
    empty.textContent = err.message;
  }
}

document.getElementById("searchBtn").addEventListener("click", doSearch);
document.getElementById("searchInput").addEventListener("keydown", (e) => { if (e.key === "Enter") doSearch(); });
document.getElementById("browseBtn").addEventListener("click", loadWords);
document.getElementById("categoryFilter").addEventListener("change", loadWords);

loadWords();
loadPending();
