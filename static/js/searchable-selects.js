(function () {
  function normalizeText(value) {
    return (value || '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase();
  }

  function enhanceSelect(select) {
    const allOptions = Array.from(select.options).map((option) => ({
      value: option.value,
      label: option.textContent || '',
      selected: option.selected,
      disabled: option.disabled,
    }));

    const wrapper = document.createElement('div');
    wrapper.className = 'searchable-select-wrapper';

    const searchInput = document.createElement('input');
    searchInput.type = 'search';
    searchInput.className = 'form-control searchable-select-input';
    searchInput.placeholder = select.dataset.searchPlaceholder || 'Pesquisar...';
    searchInput.autocomplete = 'off';

    const fieldLabel =
      select.getAttribute('aria-label') ||
      select.name ||
      'opcoes';
    searchInput.setAttribute('aria-label', `Pesquisar ${fieldLabel}`);

    const parent = select.parentNode;
    parent.insertBefore(wrapper, select);
    wrapper.appendChild(searchInput);
    wrapper.appendChild(select);

    function renderOptions(term) {
      const normalizedTerm = normalizeText(term.trim());
      const currentValue = select.value;

      select.innerHTML = '';

      allOptions.forEach((item) => {
        const label = item.label || '';
        const matches = !normalizedTerm || normalizeText(label).includes(normalizedTerm);
        const keepSelected = currentValue && item.value === currentValue;

        if (!matches && !keepSelected) {
          return;
        }

        const option = document.createElement('option');
        option.value = item.value;
        option.textContent = item.label;
        option.disabled = item.disabled;
        option.selected = keepSelected || (!currentValue && item.selected);
        select.appendChild(option);
      });
    }

    searchInput.addEventListener('input', function () {
      renderOptions(searchInput.value);
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    document
      .querySelectorAll('select[data-searchable="true"]')
      .forEach(enhanceSelect);
  });
})();
