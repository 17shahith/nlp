/** Rules page: fetch and render every rule as a card. */

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

async function loadRules() {
  const grid = document.getElementById("ruleGrid");
  grid.innerHTML = '<div class="muted">Loading rules...</div>';
  try {
    const { items } = await Api.rules();
    grid.innerHTML = "";
    items.forEach((rule) => {
      const card = el("div", "card rule-card");
      card.appendChild(el("h3", null, `${rule.id} — ${rule.name}`));
      card.appendChild(el("p", null, rule.description));
      if (rule.example) {
        card.appendChild(el("p", "example", `Example: ${rule.example}`));
      }
      card.appendChild(el("p", `rule-type ${rule.hard ? "blocking" : "warning"}`, rule.hard ? "Blocking rule" : "Warning only"));
      grid.appendChild(card);
    });
  } catch (err) {
    grid.innerHTML = `<div class="card error-card">${err.message}</div>`;
  }
}

loadRules();
