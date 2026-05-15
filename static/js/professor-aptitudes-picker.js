(function () {
  function normalizeText(value) {
    return (value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase();
  }

  function initPicker(root) {
    const searchInput = root.querySelector("[data-aptitudes-search]");
    const selectAllButton = root.querySelector("[data-aptitudes-select-all]");
    const clearButton = root.querySelector("[data-aptitudes-clear]");
    const countNode = root.querySelector("[data-aptitudes-count]");
    const emptyNode = root.querySelector("[data-aptitudes-empty]");
    const items = Array.from(root.querySelectorAll("[data-aptitudes-item]"));

    const getCheckbox = (item) => item.querySelector('input[type="checkbox"]');

    function updateCount() {
      const selectedCount = items.filter((item) => {
        const checkbox = getCheckbox(item);
        return Boolean(checkbox && checkbox.checked);
      }).length;

      if (countNode) {
        countNode.textContent = String(selectedCount);
      }
    }

    function applyFilter() {
      const term = normalizeText(searchInput ? searchInput.value : "");
      let visibleCount = 0;

      items.forEach((item) => {
        const label = normalizeText(item.dataset.label || item.textContent || "");
        const matches = !term || label.includes(term);
        item.classList.toggle("is-hidden", !matches);
        if (matches) {
          visibleCount += 1;
        }
      });

      if (emptyNode) {
        emptyNode.classList.toggle("d-none", visibleCount > 0);
      }
    }

    if (searchInput) {
      searchInput.addEventListener("input", applyFilter);
    }

    if (selectAllButton) {
      selectAllButton.addEventListener("click", function () {
        items.forEach((item) => {
          if (item.classList.contains("is-hidden")) {
            return;
          }
          const checkbox = getCheckbox(item);
          if (checkbox && !checkbox.disabled) {
            checkbox.checked = true;
          }
        });
        updateCount();
      });
    }

    if (clearButton) {
      clearButton.addEventListener("click", function () {
        items.forEach((item) => {
          const checkbox = getCheckbox(item);
          if (checkbox && !checkbox.disabled) {
            checkbox.checked = false;
          }
        });
        updateCount();
      });
    }

    items.forEach((item) => {
      const checkbox = getCheckbox(item);
      if (!checkbox) {
        return;
      }
      checkbox.addEventListener("change", updateCount);
    });

    applyFilter();
    updateCount();
  }

  document.addEventListener("DOMContentLoaded", function () {
    document
      .querySelectorAll("[data-aptitudes-picker]")
      .forEach(initPicker);
  });
})();
