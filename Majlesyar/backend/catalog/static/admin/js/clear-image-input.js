(() => {
  function humanizeFieldName(fieldName) {
    return String(fieldName || "image")
      .replace(/^.*\./, "")
      .replace(/[_-]+/g, " ")
      .trim();
  }

  function getPreviewKey(fileInput) {
    return String(fileInput.name || "image")
      .replace(/\[\d+\]/g, "")
      .replace(/^.*-/, "");
  }

  function findFieldRow(fileInput) {
    return (
      fileInput.closest(".form-row") ||
      fileInput.closest(".field-row") ||
      fileInput.closest(".field-box") ||
      fileInput.parentElement
    );
  }

  function buildPreviewCard(fieldRow, previewKey, fileInput) {
    const card = document.createElement("div");
    card.className = "admin-image-preview-card admin-image-preview-card--empty";
    card.dataset.liveImagePreviewCard = previewKey;
    card.innerHTML = `
      <div class="admin-image-preview-card__eyebrow">پیش‌نمایش فایل</div>
      <div class="admin-image-preview-card__title">${humanizeFieldName(previewKey)}</div>
      <div class="admin-image-preview-card__media" data-live-image-preview-media="${previewKey}"></div>
      <div class="admin-image-preview-card__caption" data-live-image-preview-caption="${previewKey}">
        هنوز تصویری انتخاب نشده است.
      </div>
    `;
    fieldRow.appendChild(card);
    return card;
  }

  function getPreviewParts(fileInput) {
    const fieldRow = findFieldRow(fileInput);
    if (!fieldRow) {
      return null;
    }

    const previewKey = getPreviewKey(fileInput);
    const formRoot = fileInput.form || document;
    const cardSelector = `[data-live-image-preview-card="${previewKey}"]`;
    const existingCard = formRoot.querySelector(cardSelector);
    const card = existingCard || buildPreviewCard(fieldRow, previewKey, fileInput);
    const media = card.querySelector(`[data-live-image-preview-media="${previewKey}"]`);
    const caption = card.querySelector(`[data-live-image-preview-caption="${previewKey}"]`);
    return { card, media, caption };
  }

  function clearPreview(cardParts, captionText) {
    if (!cardParts) return;
    if (cardParts.media) {
      cardParts.media.innerHTML = "";
    }
    if (cardParts.caption) {
      cardParts.caption.textContent = captionText;
    }
    cardParts.card.classList.add("admin-image-preview-card--empty");
  }

  function updatePreview(fileInput) {
    const cardParts = getPreviewParts(fileInput);
    if (!cardParts) return;

    if (cardParts.card.dataset.previewObjectUrl) {
      URL.revokeObjectURL(cardParts.card.dataset.previewObjectUrl);
      delete cardParts.card.dataset.previewObjectUrl;
    }

    const selectedFile = fileInput.files && fileInput.files[0];
    if (!selectedFile) {
      if (fileInput.dataset.pendingRemoval === "1") {
        clearPreview(cardParts, "تصویر پس از ذخیره حذف خواهد شد.");
        return;
      }
      if (cardParts.media && cardParts.media.querySelector("img")) {
        if (cardParts.caption) {
          cardParts.caption.textContent = "تصویر فعلی تا زمان ذخیره باقی می‌ماند.";
        }
        cardParts.card.classList.remove("admin-image-preview-card--empty");
        return;
      }
      clearPreview(cardParts, "هنوز تصویری انتخاب نشده است.");
      return;
    }

    delete fileInput.dataset.pendingRemoval;
    const objectUrl = URL.createObjectURL(selectedFile);
    cardParts.card.dataset.previewObjectUrl = objectUrl;
    cardParts.card.classList.remove("admin-image-preview-card--empty");

    if (cardParts.media) {
      cardParts.media.innerHTML = `<img src="${objectUrl}" alt="" class="admin-image-preview-card__image" />`;
    }
    if (cardParts.caption) {
      const sizeInMegabytes = (selectedFile.size / (1024 * 1024)).toFixed(2);
      cardParts.caption.textContent = `فایل انتخابی: ${selectedFile.name} | حجم تقریبی: ${sizeInMegabytes} مگابایت`;
    }

    const clearCheckbox = findFieldRow(fileInput)?.querySelector('input[type="checkbox"][name$="-clear"]');
    if (clearCheckbox) clearCheckbox.checked = false;
  }

  function attachClearButton(fileInput) {
    if (!fileInput || fileInput.dataset.clearImageBound === "1") return;
    fileInput.dataset.clearImageBound = "1";

    const fieldRow = findFieldRow(fileInput);
    if (!fieldRow) return;

    const button = document.createElement("button");
    button.type = "button";
    button.className = "clear-image-selection-btn";
    button.textContent = "پاک کردن انتخاب تصویر";

    button.addEventListener("click", () => {
      fileInput.value = "";
      fileInput.dataset.pendingRemoval = "1";

      const clearCheckbox = fieldRow.querySelector('input[type="checkbox"][name$="-clear"]');
      if (clearCheckbox) clearCheckbox.checked = true;

      const mirrorTextInput = fieldRow.querySelector('input[type="text"][disabled]');
      if (mirrorTextInput) mirrorTextInput.value = "فایلی انتخاب نشده است";

      const cardParts = getPreviewParts(fileInput);
      fileInput.dispatchEvent(new Event("change", { bubbles: true }));
    });

    fieldRow.appendChild(button);
    updatePreview(fileInput);
    fileInput.addEventListener("change", () => updatePreview(fileInput));
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
