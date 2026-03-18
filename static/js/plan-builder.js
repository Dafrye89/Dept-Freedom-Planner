document.addEventListener("DOMContentLoaded", () => {
  const formatCurrency = (value) =>
    new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,
    }).format(value || 0);

  const updateDebtTotals = (root) => {
    const rows = root.querySelectorAll("[data-form-row]");
    let totalBalance = 0;
    let totalMinimums = 0;

    rows.forEach((row) => {
      if (row.dataset.deleted === "true") {
        return;
      }

      const balanceInput = row.querySelector('input[name$="-balance"]');
      const minimumInput = row.querySelector('input[name$="-minimum_payment"]');
      totalBalance += Number.parseFloat(balanceInput?.value || "0");
      totalMinimums += Number.parseFloat(minimumInput?.value || "0");
    });

    root
      .closest("form")
      ?.querySelector("[data-total-balance]")
      ?.replaceChildren(document.createTextNode(formatCurrency(totalBalance)));
    root
      .closest("form")
      ?.querySelector("[data-total-minimums]")
      ?.replaceChildren(document.createTextNode(formatCurrency(totalMinimums)));
  };

  document.querySelectorAll("[data-formset-root]").forEach((root) => {
    const formsContainer = root.querySelector("[data-formset-forms]");
    const totalFormsInput = root.querySelector('input[name$="-TOTAL_FORMS"]');
    const template = root.querySelector("template");

    root.querySelector("[data-add-form]")?.addEventListener("click", () => {
      const formIndex = Number(totalFormsInput.value);
      const html = template.innerHTML.replaceAll("__prefix__", String(formIndex));
      const wrapper = document.createElement("div");
      wrapper.innerHTML = html.trim();
      formsContainer.appendChild(wrapper.firstElementChild);
      totalFormsInput.value = formIndex + 1;
      updateDebtTotals(root);
    });

    root.addEventListener("click", (event) => {
      const trigger = event.target.closest("[data-remove-form]");
      if (!trigger) {
        return;
      }

      const row = trigger.closest("[data-form-row]");
      const deleteField = row.querySelector('input[name$="-DELETE"]');
      if (deleteField) {
        deleteField.checked = true;
      }
      row.dataset.deleted = "true";
      updateDebtTotals(root);
    });

    root.addEventListener("input", () => updateDebtTotals(root));
    updateDebtTotals(root);
  });
});
