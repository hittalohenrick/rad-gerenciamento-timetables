# Diagrama Resumido da Estrutura do Projeto (Para Apresentação)

## 1. Visão Geral (Raiz)

```text
rad-gerenciamento-timetables/
├── app/                    # Backend Flask (regras de negócio)
├── templates/              # Telas HTML (Jinja2)
├── static/                 # CSS e JavaScript
├── migrations/             # Versionamento do banco (Alembic)
├── tests/                  # Testes automatizados (pytest + E2E)
├── scripts/                # Seeds de dados para demo e testes
├── docs/                   # Documentação acadêmica
├── run.py                  # Inicialização da aplicação
├── config.py               # Configurações globais
├── requirements.txt        # Dependências Python
└── package.json            # Dependências/scripts E2E (Playwright)
```

## 2. Núcleo da Aplicação

```text
app/
├── __init__.py             # App factory + extensões (db, login, migrate)
├── models.py               # Entidades: User, Sala, Disciplina, Timetable, Aluno, Matricula, Presenca
├── forms.py                # Validações de formulário (WTForms)
└── routes/
    ├── auth.py             # Login, logout, registro e troca de senha
    ├── admin.py            # CRUDs administrativos e alocações
    ├── professor.py        # Turmas do professor e registro de chamada
    └── helpers.py          # Regras reutilizáveis (conflitos, validações auxiliares)
```

## 3. Interface Web

```text
templates/
├── base.html               # Layout base
├── admin_dashboard.html    # Painel do administrador
├── professor_dashboard.html# Painel do professor
├── professor_attendance.html
│                           # Tela de chamada
└── *_form.html / *.html    # Telas de listagem e formulários dos CRUDs
```

```text
static/
├── css/styles.css          # Estilo visual da aplicação
└── js/searchable-selects.js# Busca em selects com muitos registros
```

## 4. Banco e Evolução de Schema

```text
migrations/
└── versions/
    ├── a3fd5de956b3_initial_migration.py
    ├── 2c7b6c9bf6c1_add_students_enrollments_and_attendance.py
    ├── 8f31c2ab09d4_add_user_password_policy_fields.py
    └── c2b0d9c4f7a1_remove_legacy_password_policy_fields.py
```

- Responsabilidade: manter histórico de mudanças do banco de forma controlada.

## 5. Testes e Dados de Demonstração

```text
tests/
├── test_app.py             # Regras de negócio e fluxos backend
└── e2e/                    # Testes de ponta a ponta com Playwright
```

```text
scripts/
├── seed_mock_data.py       # Massa grande para demonstração
└── seed_playwright_data.py # Base previsível para E2E
```

## 6. Resumo de Explicação (fala rápida)

1. `app/` concentra regras do sistema.
2. `templates/` e `static/` formam a camada de interface.
3. `migrations/` controla a evolução do banco.
4. `tests/` garante qualidade.
5. `scripts/` prepara dados para apresentação e validação.
