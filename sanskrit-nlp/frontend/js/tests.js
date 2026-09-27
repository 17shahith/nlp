/** Tests page: run the seeded test suite via the API and render a pass/fail table. */

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

async function runAll() {
  const btn = document.getElementById("runBtn");
  const table = document.getElementById("resultsTable");
  const summary = document.getElementById("summaryRow");
  btn.disabled = true;
  table.innerHTML = "<tr><td>Running...</td></tr>";
  summary.innerHTML = "";

  try {
    const report = await Api.runTests();
    summary.innerHTML = "";
    summary.appendChild(el("span", null, `Total: ${report.total}`));
    summary.appendChild(el("span", "pass", `Passed: ${report.passed}`));
    summary.appendChild(el("span", "fail", `Failed: ${report.failed}`));

    table.innerHTML = "";
    const thead = el("tr");
    ["#", "Type", "Input", "Expected", "Actual", "Status"].forEach((h) => thead.appendChild(el("th", null, h)));
    table.appendChild(thead);

    report.results.forEach((r) => {
      const row = el("tr");
      row.appendChild(el("td", null, r.id));
      row.appendChild(el("td", null, r.type));
      row.appendChild(el("td", "devanagari", r.input || "(empty)"));
      row.appendChild(el("td", "devanagari", String(r.expected)));
      row.appendChild(el("td", "devanagari", String(r.actual)));
      const statusCell = el("td");
      statusCell.appendChild(el("span", `badge ${r.status === "PASS" ? "pass" : "fail"}`, r.status));
      row.appendChild(statusCell);
      table.appendChild(row);
    });
  } catch (err) {
    table.innerHTML = `<tr><td>${err.message}</td></tr>`;
  } finally {
    btn.disabled = false;
  }
}

document.getElementById("runBtn").addEventListener("click", runAll);
