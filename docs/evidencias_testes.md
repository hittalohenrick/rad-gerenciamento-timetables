# Evidências de Testes (Unitário + E2E)

Atualizado em: 23/04/2026

## 1. Escopo validado

### Backend (`pytest`)

Cobertura funcional principal:

- autenticação e autorização por perfil;
- regras de conflito de horário (sala/professor/aluno);
- capacidade de sala em matrícula;
- criação/edição/exclusão com regras de integridade;
- fluxo de chamada (datas válidas, futuro proibido, dia da semana coerente);
- reset e troca de senha.

### E2E (Playwright)

Cenários executados:

- fluxo administrativo de navegação e CRUD básico;
- criação completa de entidades + alocação de turma + matrícula;
- fluxo professor (restrição de acesso e chamada);
- fluxo completo ponta a ponta em um único teste (para vídeo único).

## 2. Comandos executados

```bash
.venv/bin/pytest -q
PW_VIDEO_MODE=on npm run test:e2e -- --project=chromium
```

## 3. Resultados

- `pytest`: **21 passed**
- Playwright E2E: **5 passed**

## 4. Artefatos gerados

### Vídeo funcional completo (único)

- `docs/evidencias/video_teste_funcionalidades.webm`

Este vídeo corresponde ao teste:

- `tests/e2e/full-flow.spec.js`

### Relatório completo E2E

- `docs/evidencias/playwright-report/index.html`

### Vídeos por cenário (granular)

Gerados em `test-results/` para cada teste da suíte E2E.

## 5. Como reproduzir localmente

1. Instalar dependências:

```bash
pip install -r requirements.txt
npm ci
npx playwright install chromium
```

2. Rodar testes:

```bash
.venv/bin/pytest -q
PW_VIDEO_MODE=on npm run test:e2e -- --project=chromium
```

3. Abrir relatório HTML:

```bash
npm run test:e2e:report
```

## 6. Observações técnicas

- Os E2E usam banco isolado (`/tmp/rad_timetables_playwright.db`) definido na configuração do Playwright.
- O seed determinístico da suíte E2E é executado automaticamente via `tests/e2e/global-setup.js`.
- O modo de vídeo é configurável por variável de ambiente `PW_VIDEO_MODE`.
