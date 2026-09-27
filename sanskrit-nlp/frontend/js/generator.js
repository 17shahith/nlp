/** Generator page: submit input, run the pipeline, render the trace. */

const EXAMPLES = [
  "Rama, fruit, eats",
  "बालकः, विद्यालयम्, गच्छति",
  "I, book, read",
  "boy, runs",
  "beautiful, girl, water, drinks",
];

let lastTrace = null;

function renderChips() {
  const container = document.getElementById("exampleChips");
  container.innerHTML = "";
  EXAMPLES.forEach((example) => {
    const chip = document.createElement("button");
    chip.className = "chip";
    chip.type = "button";
    chip.textContent = example;
    chip.addEventListener("click", () => {
      document.getElementById("wordsInput").value = example;
      runGenerate();
    });
    container.appendChild(chip);
  });
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function renderTable(tableEl, headers, rows) {
  tableEl.innerHTML = "";
  const thead = el("thead");
  const headRow = el("tr");
  headers.forEach((h) => headRow.appendChild(el("th", null, h)));
  thead.appendChild(headRow);
  tableEl.appendChild(thead);

  const tbody = el("tbody");
  rows.forEach((cells) => {
    const row = el("tr");
    cells.forEach((cell) => row.appendChild(cell));
    tbody.appendChild(row);
  });
  tableEl.appendChild(tbody);
}

function textCell(value, className) {
  const td = el("td", className, value === null || value === undefined ? "-" : String(value));
  return td;
}

function renderTrace(trace) {
  document.getElementById("traceCard").classList.remove("hidden");
  const steps = trace.steps;

  renderTable(
    document.getElementById("step1Table"),
    ["Input", "Sanskrit", "English", "Found"],
    steps["1_meaning"].map((row) => [
      textCell(row.input),
      textCell(row.sanskrit, "devanagari"),
      textCell(row.english),
      textCell(row.found ? "yes" : `no — ${row.reason || ""}`),
    ])
  );

  renderTable(
    document.getElementById("step2Table"),
    ["Word", "Category"],
    steps["2_classification"].map((row) => [textCell(row.word, "devanagari"), textCell(row.category)])
  );

  renderTable(
    document.getElementById("step3Table"),
    ["Word", "Role", "Gender", "Number", "Case", "Person", "Tense"],
    steps["3_grammar"].map((row) => [
      textCell(row.word, "devanagari"),
      textCell(row.role),
      textCell(row.gender),
      textCell(row.number),
      textCell(row.case),
      textCell(row.person),
      textCell(row.tense),
    ])
  );

  renderTable(
    document.getElementById("step4Table"),
    ["Rule", "Result", "Message"],
    steps["4_rules"].map((row) => [
      textCell(`${row.id} — ${row.name}`),
      textCell(row.passed ? "✓ pass" : "✗ fail", row.passed ? "badge pass" : "badge fail"),
      textCell(row.message),
    ])
  );

  document.getElementById("step5Text").textContent = steps["5_template"] || "N/A";
  document.getElementById("step6Text").textContent = steps["6_output"]
    ? `${steps["6_output"].sanskrit}  /  ${steps["6_output"].iast}  /  ${steps["6_output"].english}`
    : "N/A";
}

async function runGenerate() {
  const words = document.getElementById("wordsInput").value;
  const resultCard = document.getElementById("resultCard");
  const errorCard = document.getElementById("errorCard");
  resultCard.classList.add("hidden");
  errorCard.classList.add("hidden");
  document.getElementById("explainText").textContent = "";

  try {
    const trace = await Api.generate(words);
    lastTrace = trace;
    renderTrace(trace);

    if (trace.success && trace.steps["6_output"]) {
      const output = trace.steps["6_output"];
      document.getElementById("resultSanskrit").textContent = output.sanskrit;
      document.getElementById("resultIast").textContent = output.iast;
      document.getElementById("resultEnglish").textContent = output.english;
      resultCard.classList.remove("hidden");
    } else {
      const list = document.getElementById("errorList");
      list.innerHTML = "";
      (trace.errors || []).forEach((msg) => list.appendChild(el("li", null, msg)));
      errorCard.classList.remove("hidden");
    }
  } catch (err) {
    const list = document.getElementById("errorList");
    list.innerHTML = "";
    list.appendChild(el("li", null, err.message));
    errorCard.classList.remove("hidden");
  }
}

async function runExplain() {
  if (!lastTrace) return;
  const box = document.getElementById("explainText");
  box.textContent = "Thinking...";
  try {
    const { explanation } = await Api.explain(lastTrace);
    box.textContent = explanation;
  } catch (err) {
    box.textContent = err.message;
  }
}

document.getElementById("generateBtn").addEventListener("click", runGenerate);
document.getElementById("wordsInput").addEventListener("keydown", (e) => {
  if (e.key === "Enter") runGenerate();
});
document.getElementById("explainBtn").addEventListener("click", runExplain);

renderChips();

Api.health().then((h) => {
  if (h.groq !== "enabled") {
    document.getElementById("explainBtn").classList.add("hidden");
  }
}).catch(() => {});
