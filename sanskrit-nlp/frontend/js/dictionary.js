/** Dictionary page: search, browse, add words, and manage pending AI suggestions. */

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
    ["Lemma", "IAST", "English", "Category", "Gender", "Sample forms"].forEach((h) =>
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
      table.appendChild(row);
    });
  } catch (err) {
    table.innerHTML = `<tr><td>${err.message}</td></tr>`;
  }
}

async function submitAddWord(evt) {
  evt.preventDefault();
  const form = evt.target;
  const resultBox = document.getElementById("addWordResult");
  const data = new FormData(form);

  let forms = [];
  const formsText = data.get("forms");
  if (formsText && formsText.trim()) {
    try {
      forms = JSON.parse(formsText);
    } catch (e) {
      resultBox.textContent = "Forms must be valid JSON.";
      return;
    }
  }

  const payload = {
    lemma: data.get("lemma"),
    iast: data.get("iast"),
    english: data.get("english"),
    english_aliases: (data.get("english_aliases") || "")
      .split(",").map((s) => s.trim()).filter(Boolean),
    category: data.get("category"),
    gender: data.get("gender") || null,
    animate: data.get("animate") === "true",
    forms,
  };

  try {
    await Api.addWord(payload);
    resultBox.textContent = `Added '${payload.lemma}'.`;
    form.reset();
    loadWords();
  } catch (err) {
    resultBox.textContent = err.message;
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
document.getElementById("addWordForm").addEventListener("submit", submitAddWord);

loadWords();
loadPending();
