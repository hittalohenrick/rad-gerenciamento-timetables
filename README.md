# Sistema de Gerenciamento de Timetables

Sistema web em Flask para gerenciar turmas, professores, salas, alunos e chamada de presenca.

## Funcionalidades

- Login por perfil (`admin` e `professor`)
- Troca obrigatoria de senha no primeiro login de professor
- CRUD de salas, disciplinas, professores e alunos
- Alocacao de professores em salas/horarios (timetable)
- Alocacao de alunos em turmas
- Chamada por turma e por data (professor)
- Regras de validacao para evitar conflito de horarios
- Exclusoes protegidas via `POST` com CSRF

## Controle de acesso

- `admin`: gerencia toda a base (usuarios, turmas, alunos e alocacoes)
- `professor`: acessa somente suas turmas e registra chamada
- Admin pode resetar senha de professor (gera senha temporaria)

## Estrutura do repositorio

- `app/`: aplicacao Flask (modelos, formularios e rotas)
- `app/routes/`: rotas organizadas por modulo (`auth`, `admin`, `professor`, `helpers`)
- `templates/`: telas HTML/Jinja
- `static/`: CSS e arquivos estaticos
- `migrations/`: migracoes do banco (Alembic)
- `tests/`: testes automatizados
- `docs/`: documentacao academica e artefatos do projeto
- `create_admin.py`: script para criar usuario administrador inicial
- `run.py`: ponto de entrada da aplicacao

## Instalacao e execucao

1. Criar ambiente virtual e instalar dependencias:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

2. Configurar banco e migracoes:

```bash
export FLASK_APP=run.py
flask db upgrade
```

3. Criar usuario admin inicial:

```bash
python3 create_admin.py
```

4. Executar a aplicacao:

```bash
python3 run.py
```

Acesse `http://localhost:5000`.

## Credencial padrao do admin

- usuario: `admin`
- senha: `Admin1234`

## Testes

```bash
.venv/bin/pytest -q
```

## Testes E2E (Playwright)

1. Instalar dependencias Node:

```bash
npm install
```

2. Instalar navegador usado nos testes:

```bash
npx playwright install chromium
```

3. Executar a suite E2E:

```bash
npm run test:e2e
```

4. Abrir relatorio HTML:

```bash
npm run test:e2e:report
```

Observacoes:
- A suite E2E prepara base isolada automaticamente via `scripts/seed_playwright_data.py`.
- Credenciais da base E2E: `admin/Admin1234` e `prof.demo/ProfDemo123`.

## Dados mockados (Ciencia da Computacao)

Para popular o banco com volume alto e dados realistas no cenario de Ciencia da Computacao (professores, alunos, turmas, matriculas e presencas):

```bash
.venv/bin/python scripts/seed_mock_data.py \
  --replace-existing \
  --professores 100 \
  --salas 45 \
  --disciplinas 60 \
  --alunos 1500 \
  --timetables 520 \
  --attendance-days 6
```

## Documentacao

Veja [docs/README.md](docs/README.md) para o indice de documentos.
