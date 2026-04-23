# Documentação Geral Final - Projeto RAD em Python

Atualizado em: 23/04/2026

## 1. Objetivo do projeto

O **RAD Gerenciamento de Timetables** é uma aplicação web em Python (Flask) para gestão acadêmica.

### Problema que o projeto resolve

Em operação manual (planilhas e mensagens), a gestão de turmas tende a gerar:

- conflito de horários de professor e sala;
- matrículas em turmas sobrepostas;
- perda de rastreabilidade da chamada;
- retrabalho em ajustes de grade.

### Objetivo funcional

Centralizar em uma única aplicação:

- cadastro de estrutura acadêmica;
- composição de turmas com validações;
- matrícula de alunos com regras de capacidade e choque de horário;
- chamada por professor com regra de data.

## 2. Escolhas técnicas e justificativas

## 2.1 Linguagem: Python

- legibilidade alta para banca acadêmica;
- ecossistema maduro para web e testes;
- ótima velocidade de prototipação (RAD).

## 2.2 Framework: Flask

- simples e explícito;
- permite arquitetura limpa por módulos de rota;
- integração direta com SQLAlchemy, WTForms e Login.

## 2.3 Persistência: SQLite + SQLAlchemy

- SQLite facilita execução local sem infraestrutura externa;
- SQLAlchemy permite modelagem relacional clara e validável;
- constraints e relações ficam explícitas no domínio.

## 2.4 Migrações: Alembic/Flask-Migrate

- controla evolução do schema;
- evita divergência de banco entre ambientes;
- mantém histórico auditável.

## 2.5 Autenticação: Flask-Login

- controle de sessão robusto;
- proteção de rotas por perfil;
- fluxo simples de login/logout.

## 2.6 Formulários/validação: Flask-WTF + WTForms

- validações por campo e por regra;
- integração com CSRF para ações sensíveis;
- feedback de erro diretamente na UI.

## 2.7 Frontend: Jinja + Bootstrap + CSS/JS próprios

- entrega rápida e previsível;
- sem complexidade de SPA para o escopo acadêmico;
- customizações pontuais para experiência de uso.

## 2.8 Testes: pytest + Playwright

- `pytest`: valida regras de negócio e integrações do backend;
- Playwright: valida fluxo real de interface ponta a ponta;
- suporte a vídeo e relatório para evidência de entrega.

## 3. Arquitetura e como os módulos trabalham entre si

## 3.1 Fluxo macro de uma requisição

1. Usuário acessa rota (`app/routes/*`).
2. Rota instancia formulário (`app/forms.py`).
3. Regras de negócio são aplicadas (`routes` + `helpers`).
4. Persistência ocorre via modelos (`app/models.py` + `db.session`).
5. Resposta retorna em template (`templates/*`) com CSS/JS (`static/*`).

## 3.2 Separação por responsabilidades

- **Domínio e dados**: `models.py`
- **Entrada e validação**: `forms.py`
- **Casos de uso**: `routes/admin.py`, `routes/professor.py`, `routes/auth.py`
- **Regras compartilhadas**: `routes/helpers.py`
- **Apresentação**: `templates/` + `static/`
- **Evolução de banco**: `migrations/`
- **Qualidade**: `tests/`

## 4. Estrutura da raiz (arquivo/pasta por arquivo/pasta)

Abaixo está a explicação **um a um** dos elementos principais da raiz do repositório.

## 4.1 `.codex`

Arquivo de contexto do ambiente de desenvolvimento assistido.
Não participa da lógica da aplicação.

## 4.2 `.git/`

Metadados do versionamento Git (histórico, objetos, refs).
Não participa da execução da aplicação, mas é essencial para rastreabilidade de mudanças.

## 4.3 `.editorconfig`

Padroniza estilo básico de formatação em editores (indentação, charset etc.), reduzindo inconsistência entre máquinas.

## 4.4 `.gitignore`

Define arquivos não versionados (cache, venv, banco local, artefatos E2E etc.).
Evita “lixo” no versionamento.

## 4.5 `.pytest_cache/`

Cache local de execução do pytest.
Não faz parte da lógica de negócio.

## 4.6 `__pycache__/`

Bytecode compilado do Python em ambiente local.
Também não é parte funcional do produto.

## 4.7 `.venv/` (ambiente local)

Ambiente virtual Python da máquina de desenvolvimento.
Não é parte do produto, é infraestrutura local para execução.

## 4.8 `README.md`

Guia rápido de projeto: setup, execução, testes e links de documentação.
Ponto de entrada para quem clona o repositório.

## 4.9 `config.py`

Centraliza configurações globais:

- `SECRET_KEY`;
- `SQLALCHEMY_DATABASE_URI`;
- normalização de URL de banco.

É consumido por `app/__init__.py` na criação da aplicação.

## 4.10 `run.py`

Ponto de entrada do servidor Flask em desenvolvimento.
Importa `create_app()` e inicia `app.run()`.

## 4.11 `create_admin.py`

Script utilitário para garantir existência de um admin inicial.
Usado no bootstrap de ambiente.

## 4.12 `requirements.txt`

Dependências Python do backend e testes unitários.
Instalado via `pip install -r requirements.txt`.

## 4.13 `package.json`

Dependências/scrips Node para E2E Playwright:

- executar testes;
- abrir relatório.

## 4.14 `package-lock.json`

Congela versões Node para reproduzibilidade dos testes E2E.

## 4.15 `playwright.config.js`

Configuração E2E:

- baseURL;
- webServer para ambiente de teste;
- reporter HTML;
- política de vídeo (`PW_VIDEO_MODE`).

## 4.16 `app/`

Núcleo da aplicação Flask.
Detalhamento por arquivo na seção 5.

## 4.17 `migrations/`

Controle versionado de schema Alembic.
Garante evolução consistente do banco.

## 4.18 `scripts/`

Scripts de seed:

- massa para apresentação (`seed_mock_data.py`);
- base determinística para E2E (`seed_playwright_data.py`).

## 4.19 `templates/`

Camada HTML/Jinja, com telas por caso de uso.

## 4.20 `static/`

Arquivos estáticos:

- `css/styles.css`;
- `js/searchable-selects.js`;
- `js/time-24h-spinner.js`.

## 4.21 `tests/`

Testes automatizados:

- unitário/integrado (`test_app.py`);
- ponta a ponta (`tests/e2e/*`).

## 4.22 `docs/`

Documentação acadêmica, técnica e evidências finais.

## 4.23 `instance/`

Pasta de runtime local (ex.: `app.db`).
Não é fonte de código.

## 5. Arquivos da aplicação (como trabalham entre si)

## 5.1 `app/__init__.py`

Responsável por:

- inicializar `db`, `login_manager` e `migrate`;
- configurar app pela fábrica `create_app`;
- registrar blueprint de rotas;
- habilitar `PRAGMA foreign_keys=ON` no SQLite.

Integra com:

- `config.py` (configurações);
- `app/models.py` (metadata ORM);
- `app/routes/__init__.py` (rotas).

## 5.2 `app/models.py`

Define entidades e relacionamentos principais:

- `User`
- `Sala`
- `Disciplina`
- `Timetable`
- `Aluno`
- `Matricula`
- `Presenca`

Também define constraints de unicidade para garantir integridade.
É consumido pelas rotas para persistência e leitura.

## 5.3 `app/forms.py`

Define formulários WTForms e validações customizadas.
Exemplos:

- validação de hora `HH:MM`;
- validação de data `DD/MM/AAAA` para chamada;
- validação de faixa de horário.

Rotas usam esses formulários para validar entrada antes de gravar no banco.

## 5.4 `app/routes/__init__.py`

Declara blueprint principal e agrega módulos de rota.
É o ponto de conexão entre app factory e endpoints.

## 5.5 `app/routes/auth.py`

Casos de uso de autenticação:

- login;
- logout;
- troca de senha;
- redirecionamento por perfil.

Usa `flask-login`, `LoginForm` e modelo `User`.

## 5.6 `app/routes/admin.py`

Casos de uso do perfil administrador:

- dashboards;
- CRUD de salas/disciplinas/professores/alunos;
- CRUD de turmas;
- matrícula de alunos;
- reset de senha de professor.

Orquestra chamadas a `helpers.py`, formulários e modelos.

## 5.7 `app/routes/professor.py`

Casos de uso do professor:

- visualizar turmas atribuídas;
- abrir tela de chamada;
- validar data de chamada;
- salvar presença por aluno.

Integra com `AttendanceForm` e modelos `Timetable/Presenca/Matricula`.

## 5.8 `app/routes/helpers.py`

Regras e utilitários compartilhados:

- decoradores de autorização por perfil;
- detecção de conflito de alocação;
- geração de label de turma;
- validações auxiliares de duplicidade/capacidade.

Reduz duplicação entre módulos de rota.

## 6. Templates e interface

## 6.1 `templates/base.html`

Layout base da aplicação:

- navbar por perfil;
- área de mensagens `flash`;
- carregamento de CSS/JS globais.

## 6.2 Templates de domínio

- `admin_dashboard.html`, `professor_dashboard.html`, `professor_attendance.html`
- `salas.html`, `disciplinas.html`, `professores.html`, `alunos.html`, `horarios.html`, `matriculas.html`
- `*_form.html` correspondentes
- `login.html`, `change_password.html`, `register.html`
- `_form_helpers.html` (macro de renderização de campo)

Todos recebem dados das rotas e exibem estado operacional em tabelas/formulários.

## 6.3 Arquivos estáticos

- `static/css/styles.css`: tema e responsividade.
- `static/js/searchable-selects.js`: busca em selects com muitos itens.
- `static/js/time-24h-spinner.js`: comportamento de horário com incremento por teclado em 24h.

## 7. Banco de dados e migrações

## 7.1 `migrations/env.py` e `alembic.ini`

Configuração de execução Alembic.

## 7.2 `migrations/versions/*.py`

Histórico de mudanças de schema.

Fluxo recomendado:

```bash
flask db upgrade
```

## 8. Scripts de dados

## 8.1 `scripts/seed_mock_data.py`

Gera massa de dados para apresentação (cenário acadêmico completo).

## 8.2 `scripts/seed_playwright_data.py`

Monta base determinística para E2E, garantindo reprodutibilidade dos cenários de UI.

## 9. Testes e qualidade

## 9.1 `tests/test_app.py`

Valida regras backend com banco em memória:

- autenticação/autorizações;
- conflitos de horários;
- capacidade de turma;
- regras de presença;
- fluxos administrativos.

## 9.2 `tests/e2e/*.spec.js`

Valida fluxo real de interface no navegador:

- admin;
- professor/chamada;
- fluxo completo ponta a ponta (`full-flow.spec.js`).

## 10. Evidência final de funcionamento

- Testes unitários/integrados: **21 passed**
- Testes E2E: **5 passed**
- Vídeo funcional completo: `docs/evidencias/video_teste_funcionalidades.webm`
- Relatório E2E: `docs/evidencias/playwright-report/index.html`

## 11. Estado final da solução

O sistema está pronto para apresentação acadêmica, com:

- arquitetura limpa e modular;
- regras de negócio consistentes;
- interface funcional por perfil;
- documentação técnica consolidada;
- evidências automatizadas de qualidade (teste + vídeo + relatório).
