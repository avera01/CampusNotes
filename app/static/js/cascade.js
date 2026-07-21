/**
 * Wires up a University -> Course -> Semester -> Subject chain of <select>
 * elements. Each select after the first is populated by fetching a JSON
 * endpoint that depends on the previous select's value.
 *
 * levels: array of { select: HTMLSelectElement, endpoint: string, param: string,
 *                     placeholder: string }
 * `endpoint` is called as `${endpoint}?${param}=${previousValue}`.
 * The first level's select is assumed to already have its options rendered
 * server-side (from the University list) and is not fetched.
 */
function initCascade(levels) {
  function resetFrom(index, placeholder) {
    const select = levels[index].select;
    select.innerHTML = "";
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = placeholder;
    select.appendChild(opt);
    select.disabled = true;
  }

  function populate(index, items) {
    const { select, placeholder } = levels[index];
    select.innerHTML = "";
    const emptyOpt = document.createElement("option");
    emptyOpt.value = "";
    emptyOpt.textContent = placeholder;
    select.appendChild(emptyOpt);

    items.forEach((item) => {
      const opt = document.createElement("option");
      opt.value = item.id;
      opt.textContent = item.label;
      select.appendChild(opt);
    });
    select.disabled = items.length === 0;
  }

  function loadLevel(index) {
    if (index >= levels.length) return;
    const prev = levels[index - 1];
    const value = prev.select.value;

    // Reset every level below this one first.
    for (let i = index; i < levels.length; i++) {
      resetFrom(i, levels[i].placeholder);
    }
    if (!value) return;

    fetch(`${levels[index].endpoint}?${levels[index].param}=${encodeURIComponent(value)}`)
      .then((res) => res.json())
      .then((items) => populate(index, items))
      .catch(() => populate(index, []));
  }

  levels.forEach((level, index) => {
    if (index === 0) return; // first select is server-rendered, not fetched
    level.select.addEventListener("change", () => loadLevel(index + 1));
  });

  levels[0].select.addEventListener("change", () => loadLevel(1));

  // Start everything below level 0 disabled until a value is chosen above it.
  for (let i = 1; i < levels.length; i++) {
    resetFrom(i, levels[i].placeholder);
  }
}
