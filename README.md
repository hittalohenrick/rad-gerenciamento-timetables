# Sistema de Gerenciamento de Timetables (RAD Python)

Aplicação web em Flask para gestão acadêmica de turmas (`timetables`), com perfis `admin` e `professor`, validações de conflito e fluxo completo de chamada.

## Objetivo

Centralizar operações acadêmicas que normalmente ficam em planilhas:

- cadastro e manutenção de salas, disciplinas, professores e alunos;
- criação de turmas com regras de conflito de sala/professor;
- matrícula de alunos com controle de capacidade e conflito de horário;
- chamada por professor com validação de data.

## Funcionalidades principais

- Login por `username` e senha.
- Perfis com autorização por rota (`admin` e `professor`).
- CRUD de salas, disciplinas, professores e alunos.
- CRUD de turmas (`timetable`).
- Alocação de alunos em turmas.
- Chamada por turma e data.
- Regras de integridade de negócio + constraints no banco.

## Arquitetura resumida

- `app/models.py`: entidades SQLAlchemy.
- `app/forms.py`: validações WTForms.
- `app/routes/`: orquestração de fluxos (`auth`, `admin`, `professor`, `helpers`).
- `templates/` + `static/`: interface Jinja/CSS/JS.
- `migrations/`: evolução do schema com Alembic.
- `tests/`: testes unitários/integrados (`pytest`) e E2E (Playwright).

## Requisitos

- Python 3.12+
- Node.js 18+

## Setup local

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
npm ci
npx playwright install chromium
```

## Banco e inicialização

```bash
export FLASK_APP=run.py
flask db upgrade
python3 create_admin.py
python3 run.py
```

Acesse `http://127.0.0.1:5000`.

## Credenciais

- Admin padrão: `admin` / `Admin1234`
- Professores mockados (seeds): senha padrão definida por script (`123456` quando padronizado)

## Massa de dados para apresentação

```bash
.venv/bin/python scripts/seed_mock_data.py \
  --replace-existing \
  --professores 7 \
  --disciplinas 6 \
  --salas 7 \
  --alunos 140 \
  --timetables 42 \
  --attendance-days 4
```

## Testes

### Unitários / integração

```bash
.venv/bin/pytest -q
```

### E2E com vídeo

```bash
PW_VIDEO_MODE=on npm run test:e2e -- --project=chromium
```

## Evidências geradas

- Vídeo funcional completo: `docs/evidencias/video_teste_funcionalidades.webm`
- Relatório Playwright: `docs/evidencias/playwright-report/index.html`

## Documentação final

- Índice geral: [`docs/README.md`](docs/README.md)
- Documentação geral final (arquivo a arquivo): [`docs/documentacao_geral_final.md`](docs/documentacao_geral_final.md)
- Evidências de testes: [`docs/evidencias_testes.md`](docs/evidencias_testes.md)
