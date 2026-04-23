# Diagrama da Estrutura do Projeto (Detalhado)

Atualizado em: 23/04/2026

```text
rad-gerenciamento-timetables/
├── .editorconfig
├── .gitignore
├── README.md
├── config.py
├── run.py
├── create_admin.py
├── requirements.txt
├── package.json
├── package-lock.json
├── playwright.config.js
│
├── app/
│   ├── __init__.py
│   ├── forms.py
│   ├── models.py
│   └── routes/
│       ├── __init__.py
│       ├── auth.py
│       ├── admin.py
│       ├── professor.py
│       └── helpers.py
│
├── migrations/
│   ├── alembic.ini
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── a3fd5de956b3_initial_migration.py
│       ├── 2c7b6c9bf6c1_add_students_enrollments_and_attendance.py
│       ├── 8f31c2ab09d4_add_user_password_policy_fields.py
│       └── c2b0d9c4f7a1_remove_legacy_password_policy_fields.py
│
├── scripts/
│   ├── seed_mock_data.py
│   └── seed_playwright_data.py
│
├── static/
│   ├── css/
│   │   └── styles.css
│   └── js/
│       ├── searchable-selects.js
│       └── time-24h-spinner.js
│
├── templates/
│   ├── base.html
│   ├── _form_helpers.html
│   ├── login.html
│   ├── change_password.html
│   ├── register.html
│   ├── admin_dashboard.html
│   ├── professor_dashboard.html
│   ├── professor_attendance.html
│   ├── horarios.html
│   ├── timetable_form.html
│   ├── matriculas.html
│   ├── matricula_form.html
│   ├── professores.html
│   ├── disciplinas.html
│   ├── disciplina_form.html
│   ├── salas.html
│   ├── sala_form.html
│   ├── alunos.html
│   └── aluno_form.html
│
├── tests/
│   ├── test_app.py
│   └── e2e/
│       ├── global-setup.js
│       ├── admin-flows.spec.js
│       ├── professor-attendance.spec.js
│       ├── full-flow.spec.js
│       └── helpers/
│           └── ui-helpers.js
│
└── docs/
    ├── README.md
    ├── entregas.md
    ├── diagrama_estrutura_projeto.md
    ├── diagrama_estrutura_projeto_resumido.md
    ├── estrutura_projeto_slide_pronto.md
    ├── evidencias_testes.md
    ├── documentacao_geral_final.md
    ├── projeto/
    │   ├── documento_modelagem.md
    │   ├── documento_prototipo_interface.md
    │   ├── relatorio.md
    │   └── memorial_tecnico_tcc.md
    └── evidencias/
        ├── video_teste_funcionalidades.webm
        └── playwright-report/
```

## Leitura rápida

- `app/` concentra regras e casos de uso.
- `templates/` e `static/` formam a interface.
- `migrations/` versiona o banco.
- `tests/` valida backend e interface real.
- `docs/evidencias/` guarda vídeo e relatório de execução final.
