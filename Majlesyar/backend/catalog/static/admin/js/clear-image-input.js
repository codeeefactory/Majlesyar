(() => {
  function attachClearButton(fileInput) {
    if (!fileInput || fileInput.dataset.clearImageBound === "1") return;
    fileInput.dataset.clearImageBound = "1";

    const fieldRow =
      fileInput.closest(".form-row") ||
      fileInput.closest(".field-row") ||
      fileInput.closest(".field-box");
    if (!fieldRow) return;

    const button = document.createElement("button");
    button.type = "button";
    button.className = "clear-image-selection-btn";
    button.textContent = "پاک کردن انتخاب تصویر";

    button.addEventListener("click", () => {
      fileInput.value = "";

      const clearCheckbox = fieldRow.querySelector('input[type="checkbox"][name$="-clear"]');
      if (clearCheckbox) clearCheckbox.checked = true;

      const mirrorTextInput = fieldRow.querySelector('input[type="text"][disabled]');
      if (mirrorTextInput) mirrorTextInput.value = "فایلی انتخاب نشده است";

      fileInput.dispatchEvent(new Event("change", { bubbles: true }));
    });

    fieldRow.appendChild(button);
  }

  function initClearButtons() {
    const inputs = document.querySelectorAll('.unfold input[type="file"]');
    inputs.forEach((input) => attachClearButton(input));
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initClearButtons, { once: true });
  } else {
    initClearButtons();
  }
})();
