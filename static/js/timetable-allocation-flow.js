(function () {
  function parseJsonPayload(rawJson) {
    if (!rawJson) {
      return {};
    }
    try {
      const parsed = JSON.parse(rawJson);
      return parsed && typeof parsed === 'object' ? parsed : {};
    } catch (_error) {
      return {};
    }
  }

  function asIntOrNull(value) {
    if (value === null || value === undefined || value === '') {
      return null;
    }
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  function snapshotOptions(selectElement) {
    return Array.from(selectElement.options).map(function (option) {
      return {
        value: option.value,
        label: option.textContent || '',
        disabled: Boolean(option.disabled),
      };
    });
  }

  function buildOption(value, label, disabled) {
    const option = document.createElement('option');
    option.value = String(value);
    option.textContent = label;
    option.disabled = Boolean(disabled);
    return option;
  }

  function initAllocationFlow() {
    const payloadNode = document.getElementById('timetable-allocation-data');
    const daySelect = document.getElementById('dia');
    const slotSelect = document.getElementById('horario_id');
    const turmaSelect = document.getElementById('turma_id');
    const disciplinaSelect = document.getElementById('disciplina_id');
    const professorSelect = document.getElementById('professor_id');
    const roomSelect = document.getElementById('sala_id');
    const noteElement = document.getElementById('allocation-availability-note');

    if (!payloadNode || !daySelect || !slotSelect || !disciplinaSelect || !professorSelect || !roomSelect) {
      return;
    }

    const submitButton = daySelect.form
      ? daySelect.form.querySelector('button[type="submit"], input[type="submit"]')
      : null;

    const payload = parseJsonPayload(payloadNode.textContent);
    const availabilityByKey = payload.availability_by_key || {};
    const combinations = Object.values(availabilityByKey);
    const professorToDisciplina = payload.professor_to_disciplina || {};
    const turmaToDisciplina = payload.turma_to_disciplina || {};

    const optionCatalog = {
      dia: snapshotOptions(daySelect),
      horario: snapshotOptions(slotSelect),
      turma: turmaSelect ? snapshotOptions(turmaSelect) : [],
      disciplina: snapshotOptions(disciplinaSelect),
      professor: snapshotOptions(professorSelect),
      sala: snapshotOptions(roomSelect),
    };

    function selectedValues() {
      return {
        dia: daySelect.value || null,
        horario: slotSelect.value || null,
        turma: turmaSelect ? asIntOrNull(turmaSelect.value) : null,
        disciplina: asIntOrNull(disciplinaSelect.value),
        professor: asIntOrNull(professorSelect.value),
        sala: asIntOrNull(roomSelect.value),
      };
    }

    function professorDisciplinaIds(professorId) {
      const ids = professorToDisciplina[String(professorId)];
      if (!Array.isArray(ids)) {
        return [];
      }
      return ids
        .map(function (idValue) {
          return Number(idValue);
        })
        .filter(function (idValue) {
          return Number.isFinite(idValue);
        });
    }

    function turmaDisciplinaIds(turmaId) {
      const ids = turmaToDisciplina[String(turmaId)];
      if (!Array.isArray(ids)) {
        return [];
      }
      return ids
        .map(function (idValue) {
          return Number(idValue);
        })
        .filter(function (idValue) {
          return Number.isFinite(idValue);
        });
    }

    function professorCanTeach(professorId, disciplinaId) {
      if (!professorId || !disciplinaId) {
        return true;
      }
      const aptas = professorDisciplinaIds(professorId);
      if (!aptas.length) {
        return false;
      }
      return aptas.includes(Number(disciplinaId));
    }

    function comboMatches(combo, selections) {
      if (selections.dia && combo.day !== selections.dia) {
        return false;
      }
      if (selections.horario && combo.slot_id !== selections.horario) {
        return false;
      }
      if (selections.sala && !combo.sala_ids.includes(selections.sala)) {
        return false;
      }
      if (selections.professor && !combo.professor_ids.includes(selections.professor)) {
        return false;
      }
      if (selections.turma && !combo.turma_ids.includes(selections.turma)) {
        return false;
      }

      if (selections.turma && selections.disciplina) {
        const turmaDisciplinas = turmaDisciplinaIds(selections.turma);
        if (!turmaDisciplinas.includes(selections.disciplina)) {
          return false;
        }
      }

      if (selections.turma && !selections.disciplina) {
        const turmaDisciplinas = turmaDisciplinaIds(selections.turma);
        if (!turmaDisciplinas.length) {
          return false;
        }
      }

      if (selections.disciplina && selections.professor) {
        return professorCanTeach(selections.professor, selections.disciplina);
      }

      if (selections.disciplina && !selections.professor) {
        return combo.professor_ids.some(function (professorId) {
          return professorCanTeach(professorId, selections.disciplina);
        });
      }

      if (selections.professor && !selections.disciplina) {
        return professorDisciplinaIds(selections.professor).length > 0;
      }

      return true;
    }

    function hasFeasibleCombination(selections) {
      return combinations.some(function (combo) {
        return comboMatches(combo, selections);
      });
    }

    function allowedForField(fieldName, rawValue, currentSelections) {
      const nextSelections = {
        dia: currentSelections.dia,
        horario: currentSelections.horario,
        turma: currentSelections.turma,
        disciplina: currentSelections.disciplina,
        professor: currentSelections.professor,
        sala: currentSelections.sala,
      };

      if (fieldName === 'dia') {
        nextSelections.dia = rawValue || null;
      } else if (fieldName === 'horario') {
        nextSelections.horario = rawValue || null;
      } else if (fieldName === 'turma') {
        nextSelections.turma = asIntOrNull(rawValue);
      } else if (fieldName === 'disciplina') {
        nextSelections.disciplina = asIntOrNull(rawValue);
      } else if (fieldName === 'professor') {
        nextSelections.professor = asIntOrNull(rawValue);
      } else if (fieldName === 'sala') {
        nextSelections.sala = asIntOrNull(rawValue);
      }

      if (fieldName === 'turma' && Number(rawValue) === 0) {
        nextSelections.turma = null;
      }

      return hasFeasibleCombination(nextSelections);
    }

    function applyFilteredOptions(selectElement, fieldName, options, selections) {
      const previousValue = selectElement.value;
      const allowed = options.filter(function (option) {
        if (!option.value) {
          return true;
        }
        return allowedForField(fieldName, option.value, selections);
      });

      selectElement.innerHTML = '';

      if (!allowed.length) {
        selectElement.appendChild(buildOption('', 'Sem opcoes disponiveis', true));
        selectElement.disabled = true;
        return false;
      }

      selectElement.disabled = false;
      allowed.forEach(function (optionData) {
        const option = buildOption(optionData.value, optionData.label, optionData.disabled);
        selectElement.appendChild(option);
      });

      const hasPrevious = allowed.some(function (optionData) {
        return String(optionData.value) === String(previousValue);
      });
      if (hasPrevious) {
        selectElement.value = previousValue;
      } else if (fieldName === 'turma') {
        const hasNoTurma = allowed.some(function (optionData) {
          return String(optionData.value) === '0';
        });
        if (hasNoTurma) {
          selectElement.value = '0';
        } else {
          selectElement.selectedIndex = 0;
        }
      } else {
        selectElement.selectedIndex = 0;
      }

      return true;
    }

    function updateAvailabilityNote(selections) {
      if (!noteElement) {
        return;
      }

      const slotKey = `${selections.dia || ''}|${selections.horario || ''}`;
      const slotData = availabilityByKey[slotKey];
      if (!slotData) {
        noteElement.textContent = 'Nao foi possivel calcular disponibilidade para a combinacao selecionada.';
        return;
      }

      const roomCount = slotData.sala_ids.length;
      const professorCount = slotData.professor_ids.length;
      const turmaCount = slotData.turma_ids.length;
      noteElement.textContent = `${roomCount} sala(s), ${professorCount} professor(es) e ${turmaCount} turma(s) disponivel(is) para ${slotData.day} no ${slotData.slot_label}.`;
    }

    function refreshAll() {
      const selectionsBefore = selectedValues();

      const fields = [
        { name: 'dia', select: daySelect },
        { name: 'horario', select: slotSelect },
      ];
      if (turmaSelect) {
        fields.push({ name: 'turma', select: turmaSelect });
      }
      fields.push({ name: 'disciplina', select: disciplinaSelect });
      fields.push({ name: 'professor', select: professorSelect });
      fields.push({ name: 'sala', select: roomSelect });

      let allValid = true;
      fields.forEach(function (field) {
        const ok = applyFilteredOptions(field.select, field.name, optionCatalog[field.name], selectionsBefore);
        allValid = allValid && ok;
      });

      const selectionsAfter = selectedValues();
      updateAvailabilityNote(selectionsAfter);
      if (submitButton) {
        submitButton.disabled = !allValid || !hasFeasibleCombination(selectionsAfter);
      }
    }

    [daySelect, slotSelect, turmaSelect, disciplinaSelect, professorSelect, roomSelect]
      .filter(Boolean)
      .forEach(function (selectElement) {
        selectElement.addEventListener('change', refreshAll);
      });

    refreshAll();
  }

  document.addEventListener('DOMContentLoaded', initAllocationFlow);
})();
