(function () {
  "use strict";

  const fmt = (v) => {
    if (v === null || v === undefined || isNaN(v)) return "—";
    return "$" + Number(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  const num = (el) => {
    if (!el) return 0;
    const v = parseFloat(el.value);
    return isNaN(v) ? 0 : v;
  };

  function balanceRow(input) {
    return input.closest(".balance-row");
  }

  function recompute() {
    const c1 = num(document.getElementById("c1_salary"));
    const c2 = num(document.getElementById("c2_salary"));
    const out = num(document.getElementById("outflow"));
    const ded = num(document.getElementById("deductibles"));

    const inflow = c1 + c2;
    const excess = inflow - out;
    const target = 6 * out + ded;

    document.getElementById("t_inflow").textContent = fmt(inflow);
    document.getElementById("t_outflow").textContent = fmt(out);
    document.getElementById("t_excess").textContent = fmt(excess);
    document.getElementById("t_target").textContent = fmt(target);

    let c1Ret = 0, c2Ret = 0, nonRet = 0, trust = 0, liab = 0;
    let missing = 0;

    document.querySelectorAll("[data-balance]").forEach((inp) => {
      const row = balanceRow(inp);
      const cat = row.dataset.cat;
      const owner = row.dataset.owner;
      const v = num(inp);
      const rawEmpty = inp.value === "" || inp.value === null;
      if (rawEmpty) {
        row.classList.add("missing");
        missing++;
      } else {
        row.classList.remove("missing");
      }
      if (cat === "retirement" && owner === "client1") c1Ret += v;
      else if (cat === "retirement" && owner === "client2") c2Ret += v;
      else if (cat === "non_retirement") nonRet += v;
      else if (cat === "trust") trust += v;
      else if (cat === "liability") liab += v;
    });

    const grand = c1Ret + c2Ret + nonRet + trust;
    const setIf = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = fmt(v); };
    setIf("t_c1_ret", c1Ret);
    setIf("t_c2_ret", c2Ret);
    setIf("t_non_ret", nonRet);
    setIf("t_trust", trust);
    setIf("t_grand", grand);
    setIf("t_liab", liab);

    const btn = document.getElementById("submit-btn");
    if (btn) {
      btn.disabled = missing > 0;
      btn.textContent = missing > 0 ? `Generate Report (${missing} missing)` : "Generate Report";
    }
  }

  document.addEventListener("input", (e) => {
    if (e.target.matches("[data-live], [data-balance]")) recompute();
  });

  document.addEventListener("click", (e) => {
    if (!e.target.matches("[data-use-last]")) return;
    const id = e.target.dataset.id;
    const balVal = e.target.dataset.balanceVal;
    const dateVal = e.target.dataset.dateVal;
    const balInp = document.querySelector(`[data-balance][data-id="${id}"]`);
    const dateInp = document.querySelector(`[data-date][data-id="${id}"]`);
    if (balInp && balVal !== "") balInp.value = balVal;
    if (dateInp && dateVal) dateInp.value = dateVal;
    recompute();
  });

  recompute();
})();
