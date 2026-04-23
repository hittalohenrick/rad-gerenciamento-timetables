# Diagrama da Estrutura do Projeto

```text
/home/hittalohenrick/Projetos-isolados/rad-gerenciamento-timetables/
├── .codex                                  # Marcador/arquivo de contexto do ambiente Codex
├── .editorconfig                           # Padronização de formatação entre editores
├── .git/                                   # Metadados do Git (histórico, refs, objetos)
├── .gitignore                              # Arquivos/pastas ignorados pelo Git
├── .pytest_cache/                          # Cache local do pytest (gerado automaticamente)
├── .venv/                                  # Ambiente virtual Python local
├── __pycache__/                            # Bytecode Python compilado
├── instance/                               # Dados locais de execução (ex.: SQLite em runtime)
│
├── README.md                               # Guia principal do projeto (setup, execução, testes)
├── config.py                               # Configurações centrais (SECRET_KEY, DATABASE_URL, etc.)
├── run.py                                  # Ponto de entrada da aplicação Flask
├── create_admin.py                         # Script para criar usuário admin inicial
├── requirements.txt                        # Dependências Python
├── package.json                            # Scripts/deps Node para E2E (Playwright)
├── package-lock.json                       # Lock das dependências Node
├── playwright.config.js                    # Configuração dos testes E2E Playwright
│
├── app/                                    # Código principal da aplicação
│   ├── __init__.py                         # App factory, init de extensões e blueprint
│   ├── models.py                           # Modelos SQLAlchemy (User, Sala, Disciplina, etc.)
│   ├── forms.py                            # Formulários WTForms e validações de entrada
│   └── routes/
│       ├── __init__.py                     # Registro/agregação dos módulos de rota
│       ├── auth.py                         # Login, logout, registro e troca de senha
│       ├── admin.py                        # Fluxos administrativos (CRUDs e alocações)
│       ├── professor.py                    # Fluxos do professor (dashboard e chamada)
│       └── helpers.py                      # Funções utilitárias/regras compartilhadas
│
├── migrations/                             # Migrações Alembic
│   ├── README                              # Instruções básicas do Alembic
│   ├── alembic.ini                         # Configuração do Alembic
│   ├── env.py                              # Ambiente de execução das migrações
│   ├── script.py.mako                      # Template de geração de novas migrações
│   └── versions/
│       ├── __init__.py                     # Marca pacote de versões
│       ├── a3fd5de956b3_initial_migration.py
│       │                                    # Migração inicial (tabelas base)
│       ├── 2c7b6c9bf6c1_add_students_enrollments_and_attendance.py
│       │                                    # Adiciona aluno/matricula/presenca
│       ├── 8f31c2ab09d4_add_user_password_policy_fields.py
│       │                                    # Migração histórica de campos de política de senha
│       └── c2b0d9c4f7a1_remove_legacy_password_policy_fields.py
│                                            # Remove campos legados para simplificar autenticação
│
├── scripts/                                # Scripts auxiliares de dados
│   ├── seed_mock_data.py                   # Gera massa de dados grande para demonstração
│   └── seed_playwright_data.py             # Base determinística para testes E2E
│
├── static/                                 # Arquivos estáticos da interface
│   ├── css/
│   │   └── styles.css                      # Estilos globais da aplicação
│   └── js/
│       └── searchable-selects.js           # Busca em campos select grandes
│
├── templates/                              # Templates Jinja2 (telas HTML)
│   ├── base.html                           # Layout base (navbar, flashes, blocos)
│   ├── _form_helpers.html                  # Macros utilitárias de render de campos
│   ├── login.html                          # Tela de login
│   ├── change_password.html                # Tela de alteração de senha
│   ├── register.html                       # Formulário de cadastro/edição de usuário
│   ├── admin_dashboard.html                # Painel principal do admin
│   ├── professor_dashboard.html            # Painel principal do professor
│   ├── professor_attendance.html           # Tela de chamada/presença da turma
│   ├── salas.html                          # Listagem de salas
│   ├── sala_form.html                      # Formulário de sala
│   ├── disciplinas.html                    # Listagem de disciplinas
│   ├── disciplina_form.html                # Formulário de disciplina
│   ├── professores.html                    # Listagem de professores
│   ├── alunos.html                         # Listagem de alunos
│   ├── aluno_form.html                     # Formulário de aluno
│   ├── horarios.html                       # Listagem de turmas/alocações
│   ├── timetable_form.html                 # Formulário de alocação de turma
│   ├── matriculas.html                     # Listagem de matrículas em turmas
│   └── matricula_form.html                 # Formulário de matrícula em turma
│
├── tests/                                  # Testes automatizados
│   ├── test_app.py                         # Testes backend (pytest)
│   └── e2e/
│       ├── global-setup.js                # Setup global da suíte E2E
│       ├── admin-flows.spec.js            # Cenários E2E do perfil admin
│       ├── professor-attendance.spec.js   # Cenários E2E do professor/chamada
│       └── helpers/
│           └── ui-helpers.js              # Helpers reutilizáveis de automação de UI
│
└── docs/                                   # Documentação acadêmica e de projeto
    ├── README.md                           # Índice da documentação
    ├── entregas.md                         # Controle de entregas
    ├── TRABALHO FINAL_CRITERIOS.md         # Critérios do trabalho final (texto)
    ├── TRABALHO FINAL_CRITÉRIOS.docx       # Critérios em formato Word
    ├── Modelo de Relatorio para o Projeto.md
    │                                        # Modelo textual de relatório
    ├── Modelo de Relatório para o Projeto.docx
    │                                        # Modelo em Word
    ├── Planejamento de Requisitos.md       # Requisitos funcionais e não funcionais
    ├── Planejamento de Requisitos.docx     # Versão Word do planejamento
    ├── Planejamento de Requisitos.pdf      # Versão PDF do planejamento
    └── projeto/
        ├── relatorio.md                    # Relatório consolidado do projeto
        ├── relatorio.docx                  # Relatório em Word
        ├── relatorio.pdf                   # Relatório em PDF
        ├── memorial_tecnico_tcc.md         # Memorial técnico detalhado
        ├── memorial_tecnico_tcc.docx       # Memorial em Word
        ├── memorial_tecnico_tcc.pdf        # Memorial em PDF
        ├── documento_modelagem.md          # Modelagem de dados (texto)
        ├── documento_modelagem.docx        # Modelagem em Word
        ├── documento_modelagem.pdf         # Modelagem em PDF
        ├── documento_prototipo_interface.md
        │                                        # Protótipo de interface (texto)
        ├── documento_prototipo_interface.docx   # Protótipo em Word
        └── documento_prototipo_interface.pdf    # Protótipo em PDF
```
