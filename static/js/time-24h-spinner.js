(function () {
  function pad2(value) {
    return String(value).padStart(2, '0');
  }

  function parseTime(value) {
    if (!value) {
      return null;
    }

    const normalized = String(value).trim();
    const compact = normalized.replace(/\D/g, '');
    if (/^\d{4}$/.test(compact) && !normalized.includes(':')) {
      const h = Number(compact.slice(0, 2));
      const m = Number(compact.slice(2, 4));
      if (h >= 0 && h <= 23 && m >= 0 && m <= 59) {
        return { hours: h, minutes: m };
      }
      return null;
    }

    const match = /^(\d{1,2}):(\d{1,2})$/.exec(normalized);
    if (!match) {
      return null;
    }

    const hours = Number(match[1]);
    const minutes = Number(match[2]);
    if (Number.isNaN(hours) || Number.isNaN(minutes)) {
      return null;
    }
    if (hours < 0 || hours > 23 || minutes < 0 || minutes > 59) {
      return null;
    }

    return { hours, minutes };
  }

  function formatTime(hours, minutes) {
    return `${pad2(hours)}:${pad2(minutes)}`;
  }

  function normalizeTimeInput(input) {
    const parsed = parseTime(input.value);
    if (!parsed) {
      return false;
    }
    input.value = formatTime(parsed.hours, parsed.minutes);
    return true;
  }

  function setCaretToSegment(input, segment) {
    const cursor = segment === 'hour' ? 0 : 3;
    input.setSelectionRange(cursor, cursor + 2);
  }

  function detectSegment(input) {
    const pos = input.selectionStart ?? input.value.length;
    return pos <= 2 ? 'hour' : 'minute';
  }

  function adjustTime(input, segment, delta) {
    const parsed = parseTime(input.value) || { hours: 0, minutes: 0 };
    let hours = parsed.hours;
    let minutes = parsed.minutes;

    if (segment === 'hour') {
      hours = (hours + delta + 24) % 24;
    } else {
      minutes = (minutes + delta + 60) % 60;
    }

    input.value = formatTime(hours, minutes);
    setCaretToSegment(input, segment);
  }

  function attachTimeBehavior(input) {
    if (input.dataset.time24Enhanced === 'true') {
      return;
    }
    input.dataset.time24Enhanced = 'true';

    input.addEventListener('keydown', function (event) {
      if (event.key !== 'ArrowUp' && event.key !== 'ArrowDown') {
        return;
      }

      event.preventDefault();
      const segment = detectSegment(input);
      const delta = event.key === 'ArrowUp' ? 1 : -1;
      adjustTime(input, segment, delta);
    });

    input.addEventListener('blur', function () {
      if (!input.value.trim()) {
        return;
      }
      if (!normalizeTimeInput(input)) {
        input.value = '';
      }
    });

    if (input.value.trim()) {
      normalizeTimeInput(input);
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('input[data-time-spinner="24h"]').forEach(attachTimeBehavior);
  });
})();
