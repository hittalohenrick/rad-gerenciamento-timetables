# Memorial Tecnico Completo - Sistema de Gerenciamento de Timetables

## 1. Identificacao do projeto

- Nome do sistema: Sistema de Gerenciamento de Timetables
- Contexto academico: Trabalho Final da disciplina de Desenvolvimento Rapido de Aplicacoes em Python (RAD)
- Stack principal: Flask + SQLAlchemy + SQLite + Jinja + Bootstrap + Testes automatizados (pytest e Playwright)
- Tipo de aplicacao: Web monolitica, com separacao por camadas e perfis de acesso

## 2. Visao geral do problema

Antes do sistema, a gestao de turmas, horarios e chamadas costuma acontecer em planilhas ou controle manual. Esse modelo traz problemas recorrentes:

1. Conflitos de horario entre professor e sala.
2. Erros de alocacao de alunos em turmas com choque de horarios.
3. Falta de rastreabilidade de presencas por turma e por data.
4. Processo lento para ajustes de grade ao longo do semestre.
5. Dificuldade para apresentar evidencias de integridade e regras de negocio.

O projeto foi construindo para resolver esse problema com um fluxo centralizado, validado e persistido em banco relacional.

## 3. Objetivo do projeto

### 3.1 Objetivo geral

Desenvolver uma aplicacao web funcional para gerenciamento academico de turmas (timetables), com CRUD completo, controle de acesso por perfil, alocacao de alunos e registro de chamada com regras de validacao.

### 3.2 Objetivos especificos

1. Permitir login de `admin` e `professor`.
2. Permitir ao `admin` gerir salas, disciplinas, professores e alunos (CRUD completo).
3. Permitir ao `admin` criar/editar/remover alocacoes de turmas (dia, horario, sala, professor, disciplina).
4. Permitir ao `admin` matricular alunos em turmas com bloqueio de conflitos.
5. Permitir ao `professor` registrar chamada por data nas turmas sob sua responsabilidade.
6. Garantir regras de integridade no banco e no backend.
7. Entregar evidencias de qualidade por meio de testes automatizados.

## 4. Motivacao e justificativa tecnica

A escolha por um sistema web com Flask foi motivada por:

1. Rapidez de prototipacao (essencial para metodologia RAD).
2. Facilidade de evolucao incremental (novas entidades e regras).
3. Integracao natural com SQLAlchemy e Flask-Login.
4. Curva de aprendizagem adequada para ambiente academico.
5. Boa base para demonstrar arquitetura, validacoes e testes em um unico repositorio.

## 5. Metodologia adotada: RAD na pratica

O desenvolvimento seguiu o racional RAD em ciclos curtos:

### 5.1 Fase 1 - Planejamento de Requisitos

Foi definido:

1. Escopo funcional (CRUDs, alocacoes, chamada).
2. Escopo nao funcional (integridade, seguranca basica, usabilidade).
3. Modelo inicial de dados.
4. Escolha de stack e estrategia de persistencia.

Artefato relacionado:

- `docs/Planejamento de Requisitos.md`

### 5.2 Fase 2 - Design do Usuario

Foi estruturado:

1. Fluxo por perfil (`admin` e `professor`).
2. Navegacao principal no `base.html`.
3. Padrões de layout, feedback visual e tabelas.
4. Iteracoes de UX para pesquisa em seletores e melhoria da tela de chamada.

Artefato relacionado:

- `docs/projeto/documento_prototipo_interface.md`

### 5.3 Fase 3 - Construcao

Foi implementado:

1. Camada de modelos e migracoes.
2. Formularios com validadores.
3. Rotas separadas por dominio (`auth`, `admin`, `professor`).
4. Templates para cada caso de uso.
5. Scripts de seed para mock realista e ambiente de E2E.

### 5.4 Fase 4 - Transicao

Foi validado:

1. Testes de unidade/integracao com `pytest`.
2. Testes E2E com `Playwright`.
3. Ajustes de regra de negocio e ajustes de UX/UI.
4. Atualizacao de documentacao final.

## 6. Arquitetura da solucao

## 6.1 Estrutura arquitetural

A aplicacao adota um monolito organizado em camadas:

1. Camada de apresentacao: `templates/` + `static/`.
2. Camada de aplicacao: `app/routes/` (orquestracao de fluxos).
3. Camada de dominio e dados: `app/models.py` + `app/forms.py`.
4. Camada de persistencia e evolucao de schema: `migrations/`.
5. Camada de qualidade: `tests/`.

## 6.2 Fabrica da aplicacao

Arquivo: `app/__init__.py`

Responsabilidades:

1. Criar app Flask (`create_app`).
2. Carregar configuracoes (`config.py`).
3. Inicializar extensoes (`db`, `login_manager`, `migrate`).
4. Garantir `PRAGMA foreign_keys=ON` no SQLite.
5. Registrar blueprint principal (`app/routes`).
6. Manter fluxo de schema centralizado em migracoes Alembic.

Decisao importante:

- O bootstrap nao cria tabelas automaticamente: toda evolucao de schema passa por `flask db upgrade`, deixando o fluxo previsivel e mais simples de explicar.

## 7. Escolha de ferramentas e justificativa (detalhada)

## 7.1 Linguagem e runtime

### Python 3.12

Por que foi escolhido:

1. Forte ecossistema web e de testes.
2. Legibilidade para avaliacao academica.
3. Excelente integracao com bibliotecas da stack Flask.

## 7.2 Framework web

### Flask 3.0

Por que foi escolhido:

1. Leveza e controle granular sobre arquitetura.
2. Facilidade para organizar por blueprints e modulos.
3. Curto tempo de desenvolvimento para RAD.

## 7.3 Persistencia e ORM

### SQLite

Por que foi escolhido:

1. Banco relacional exigido pelos criterios.
2. Zero dependencia externa para executar localmente.
3. Ideal para ambiente de demonstracao e avaliacao.

### SQLAlchemy + Flask-SQLAlchemy

Por que foi escolhido:

1. Mapeamento ORM claro para entidades academicas.
2. Suporte a constraints e relacionamentos complexos.
3. Queries composicionais para regras de negocio.

### Flask-Migrate / Alembic

Por que foi escolhido:

1. Versionamento de schema com historico auditavel.
2. Facilidade de evolucao incremental do banco.
3. Reproducao do ambiente em diferentes maquinas.

## 7.4 Autenticacao e sessao

### Flask-Login

Por que foi escolhido:

1. Controle de sessao simples e robusto.
2. Decorators `@login_required` para protecao de rotas.
3. Suporte natural para fluxo de perfil (`admin`/`professor`).

## 7.5 Validacao de entrada

### Flask-WTF + WTForms + email-validator

Por que foi escolhido:

1. Formularios declarativos com validadores.
2. Integracao com CSRF para operacoes sensiveis.
3. Mensagens de erro por campo, melhorando UX e confiabilidade.

## 7.6 Seguranca de senha

### Werkzeug security

Por que foi escolhido:

1. Hash de senha via `generate_password_hash`.
2. Verificacao segura com `check_password_hash`.
3. Evita persistir senha em texto puro.

## 7.7 Frontend

### Jinja2 + Bootstrap 5 + CSS customizado + JS nativo

Por que foi escolhido:

1. Entrega rapida de UI funcional sem complexidade de SPA.
2. Componentes responsivos prontos (Bootstrap).
3. Customizacao visual para identidade do projeto.
4. JS leve para busca em selects e operacoes de chamada.

## 7.8 Testes

### pytest

Por que foi escolhido:

1. Cobertura de regras criticas no backend.
2. Testes rapidos e deterministas com banco em memoria.
3. Boa legibilidade para correcao academica.

### Playwright

Por que foi escolhido:

1. Validacao fim a fim de fluxos reais de usuario.
2. Evidencia de que UI, regras e persistencia funcionam juntas.
3. Relatorio visual para apoio em apresentacao.

## 7.9 Dependencias de banco opcional (psycopg2/psycopg)

No `requirements.txt` existe suporte condicional para PostgreSQL.

Motivo:

1. Nao interfere no uso com SQLite.
2. Mantem portabilidade para um cenario futuro de deploy.
3. Nao viola os criterios, pois o requisito pede banco relacional (SQLite ja atende).

## 8. Modelo de dados e relacionamentos

Arquivo principal: `app/models.py`

Entidades:

1. `User` (admin/professor)
2. `Sala`
3. `Disciplina`
4. `Timetable`
5. `Aluno`
6. `Matricula`
7. `Presenca`

Relacionamentos chave:

1. `Sala 1:N Timetable`
2. `User(professor) 1:N Timetable`
3. `Disciplina 1:N Timetable`
4. `Aluno N:N Timetable` (materializado por `Matricula`)
5. `Aluno N:N Timetable por data` (materializado por `Presenca`)

Constraints relevantes:

1. `unique_dia_horario_sala`
2. `unique_dia_horario_professor`
3. `unique_aluno_turma`
4. `unique_presenca_data_aluno_turma`
5. `user.username`, `user.email`, `aluno.matricula`, `disciplina.codigo` unicos

## 9. Regras de negocio implementadas

Regras no backend (`app/routes/helpers.py`, `app/routes/admin.py`, `app/routes/professor.py`):

1. Bloqueio de sobreposicao de horario para sala/professor.
2. Bloqueio de conflito de horario do aluno ao matricular.
3. Bloqueio de matricula acima da capacidade da sala.
4. Bloqueio de exclusao de entidades com vinculos ativos.
5. Bloqueio de chamada em data futura.
6. Bloqueio de chamada com dia da semana diferente da turma.
7. Politica simples de senha (tamanho minimo).
8. Troca de senha pelo usuario autenticado.

## 10. Fluxos principais do sistema

## 10.1 Fluxo do administrador

1. Login em `/login`.
2. Redirecionamento para `/admin`.
3. Gerenciamento de entidades basicas.
4. Criacao de turmas em `/timetable/new`.
5. Alocacao de alunos em `/matricula/new`.
6. Acompanhamento do estado global pelo dashboard.

## 10.2 Fluxo do professor

1. Login em `/login`.
2. Redirecionamento para `/professor`.
3. Visualizacao de turmas atribuídas.
4. Registro de chamada em `/professor/turma/<id>/chamada`.
5. Consulta de historico recente de presencas.

## 11. Intuito de cada pasta e como se relacionam

## 11.1 Raiz do projeto

### `app/`

Camada de aplicacao principal.

1. `__init__.py`: fabrica da app e inicializacao de extensoes.
2. `models.py`: entidades e regras estruturais de dados.
3. `forms.py`: contratos de entrada e validadores.
4. `routes/`: casos de uso por dominio (auth/admin/professor/helpers).

### `templates/`

Camada de apresentacao server-side (Jinja).

1. `base.html`: layout base, navbar e mensagens flash.
2. Arquivos de listagem/formulario: telas CRUD e dashboards.
3. `professor_attendance.html`: interface de chamada com scripts de apoio.

### `static/`

Recursos estaticos da UI.

1. `css/styles.css`: identidade visual e responsividade.
2. `js/searchable-selects.js`: busca em selects de alocacao.

### `migrations/`

Historico de evolucao do banco.

1. Revisao inicial.
2. Inclusao de alunos/matriculas/presencas.
3. Inclusao de campos de senha no usuario.

### `scripts/`

Automacoes de dados e testes.

1. `seed_mock_data.py`: gera grande volume de dados realistas (Ciencia da Computacao).
2. `seed_playwright_data.py`: base deterministica para E2E.

### `tests/`

Qualidade automatizada.

1. `test_app.py`: testes unitarios/integracao backend.
2. `tests/e2e/`: cenarios ponta a ponta com Playwright.

### `docs/`

Documentacao academica e tecnica por fase RAD.

### `instance/`

Armazena o SQLite local (`app.db`) em execucao real.

Observacao:

- `app.db` nao deve ser versionado; somente a estrutura via migracoes.

## 11.2 Arquivos de orquestracao na raiz

1. `run.py`: ponto de entrada para executar a app.
2. `config.py`: configuracao central e normalizacao de `DATABASE_URL`.
3. `create_admin.py`: bootstrap de usuario admin inicial.
4. `requirements.txt`: dependencias Python.
5. `package.json` e `playwright.config.js`: dependencia e setup de E2E.

## 11.3 Relacao entre as pastas (visao integrada)

1. `routes` recebe requisicao HTTP.
2. `forms` valida os dados recebidos.
3. `models` persiste no banco.
4. `templates` renderiza resposta HTML.
5. `static` aprimora experiencia visual e interacoes.
6. `tests` valida o comportamento de ponta a ponta.
7. `docs` registra decisoes e evidencias para entrega academica.

## 12. Evolucao do schema e historico tecnico

Migracoes relevantes:

1. `a3fd5de956b3`: base inicial (`user`, `sala`, `disciplina`, `timetable`).
2. `2c7b6c9bf6c1`: ampliacao para alunos, matriculas e presencas.
3. `8f31c2ab09d4`: inclusao de campos de politica de senha no usuario.
4. `c2b0d9c4f7a1`: remocao dos campos legados para simplificar o fluxo de autenticacao.

Interpretacao arquitetural:

- O projeto evoluiu de grade basica para sistema academico completo, sem quebra de historico de banco.

## 13. Problemas enfrentados e como foram resolvidos

## 13.1 Conflitos de horario nao triviais

Problema:

- Nao bastava validar igualdade exata de horario; era necessario bloquear sobreposicoes parciais.

Solucao:

- Implementacao de regra intervalar no backend (`hora_inicio < hora_fim_alvo` e `hora_fim > hora_inicio_alvo`), aplicada para sala, professor e aluno.

## 13.2 Alocacao de alunos com alta complexidade de regra

Problema:

- Era possivel matricular aluno em turma lotada ou com choque de horario.

Solucao:

- Criadas validacoes encadeadas em `new_matricula`:
  - duplicidade na mesma turma,
  - capacidade da sala,
  - conflito de horario individual.

## 13.3 Chamada com inconsistencias de data

Problema:

- Risco de professor registrar chamada em data futura ou dia incorreto.

Solucao:

- Validacao de data no backend (`validate_attendance_date`) e mensagens explicativas para correcao.

## 13.4 Simplificacao do fluxo de autenticacao

Problema:

- Fluxo de autenticacao estava mais complexo do que o necessario para demonstracao academica.

Solucao:

- Mantido controle por perfil (`admin`/`professor`) com login simples e troca de senha opcional.

## 13.5 UX de seletores com muitos registros

Problema:

- Selecionar sala/professor/disciplina/aluno/turma em listas grandes era improdutivo.

Solucao:

- Componente de busca textual em `select` (`static/js/searchable-selects.js`), acionado por `data-searchable` nos campos WTForms.

## 13.6 Consistencia visual em telas de manutencao

Problema:

- Inconsistencia de cores/acoes em botoes e campos com autofill do navegador.

Solucao:

- Padronizacao de classes de acao (`btn-edit`, `btn-danger`, etc.) e ajuste de estilo para autofill em tema escuro.

## 13.7 Estabilidade de ambiente de demonstracao

Problema:

- Testes E2E dependem de base previsivel; dados randomicos podem gerar flakiness.

Solucao:

- Seed deterministico dedicado (`seed_playwright_data.py`) chamado no `global-setup.js`.

## 14. Qualidade e estrategia de testes

## 14.1 Testes backend (pytest)

Cobrem, entre outros:

1. Login e autorizacao por perfil.
2. Conflitos de horario de sala e professor.
3. Validacao de faixa de horario.
4. Regras de exclusao protegida.
5. Duplicidade de usuario/email.
6. Politica simples de senha.
7. Troca de senha pelo proprio usuario.
8. Cadastro de alunos.
9. Matricula com capacidade e conflito.
10. Registro de chamada e validacoes de data.

Resultado atual observado:

- 21 testes aprovados.

## 14.2 Testes E2E (Playwright)

Cobrem, entre outros:

1. Navegacao admin em telas de gestao.
2. Fluxo completo de cadastro e alocacao.
3. Restricao de acesso do professor ao painel admin.
4. Fluxo de chamada com filtro, marcacao em lote e validacoes.

## 15. Seguranca, integridade e controle de acesso

Controles implementados:

1. Senha em hash (nao texto puro).
2. CSRF em operacoes de formulario.
3. Rotas protegidas com `@login_required`.
4. Guardas por perfil (`admin_required_redirect`, `professor_required_redirect`).
5. Bloqueio de exclusao com dependencias relacionais.
6. Integridade de relacionamento por foreign keys (incluindo SQLite com PRAGMA habilitado).

## 16. Conformidade com os criterios da disciplina

Matriz de aderencia:

1. Framework Python: atendido (Flask).
2. Banco relacional: atendido (SQLite).
3. CRUD completo: atendido (salas, disciplinas, professores, alunos, timetables).
4. Minimo de 2 tabelas relacionadas: atendido (varias relacoes 1:N e N:N).
5. Validacao de dados: atendido (WTForms + regras de negocio).
6. Relatorio no modelo: atendido (documentacao em `docs/` e `docs/projeto/`).

Sobre ferramentas "restritas":

- Nao ha uso de ferramenta proibida pelos criterios do trabalho.
- Uso de Playwright e scripts auxiliares e complementar, nao substitui os requisitos obrigatorios.
- Dependencias de PostgreSQL sao opcionais e nao obrigatorias para execucao com SQLite.

## 17. Limitacoes atuais

1. Foco em execucao local (sem deploy produtivo).
2. Sem trilha de auditoria completa (quem alterou o que, quando).
3. Sem modulo de relatorios exportaveis nativos (CSV/PDF de chamada por filtro).
4. Modelo de permissao simples (apenas dois perfis).

## 18. Possiveis evolucoes

1. Painel analitico com indicadores por disciplina/turma/professor.
2. Exportacao de relatorios academicos.
3. Auditoria de alteracoes administrativas.
4. Fila de tarefas para processos pesados (ex.: exportacoes em lote).
5. Camada de API REST para integracao com sistemas externos.

## 19. Conclusao

O projeto entrega um sistema academico funcional, aderente aos criterios da disciplina e tecnicamente coerente para um contexto de RAD. Ele demonstra:

1. Planejamento com escopo claro.
2. Design orientado ao fluxo real de usuario.
3. Construcao incremental com regras de negocio robustas.
4. Transicao com validacao automatizada e refinamento final.

Em termos de maturidade academica, o sistema vai alem do CRUD basico ao incorporar controle de acesso por perfil, validacoes de calendario/presenca, integridade relacional e evidencia de qualidade por testes de backend e E2E.

## 20. Apendice A - mapa resumido de responsabilidades por arquivo

1. `app/__init__.py`: bootstrap da aplicacao.
2. `app/models.py`: entidades, constraints e relacionamentos.
3. `app/forms.py`: contratos de entrada e validacoes.
4. `app/routes/auth.py`: autenticacao, login e troca de senha.
5. `app/routes/admin.py`: casos de uso administrativos.
6. `app/routes/professor.py`: casos de uso docentes (dashboard e chamada).
7. `app/routes/helpers.py`: regras reutilizaveis de dominio.
8. `scripts/seed_mock_data.py`: massa de dados realista.
9. `scripts/seed_playwright_data.py`: base deterministica de E2E.
10. `tests/test_app.py`: validacao de regras de negocio backend.
11. `tests/e2e/*.spec.js`: validacao de fluxo de usuario real.
12. `templates/*.html`: interface e navegacao.
13. `static/css/styles.css`: linguagem visual.
14. `static/js/searchable-selects.js`: usabilidade em selects grandes.

## 21. Apendice B - comandos essenciais do projeto

Execucao local:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export FLASK_APP=run.py
flask db upgrade
python create_admin.py
python run.py
```

Testes backend:

```bash
.venv/bin/pytest -q
```

Testes E2E:

```bash
npm install
npx playwright install chromium
npm run test:e2e
```

Carga de dados mockados:

```bash
.venv/bin/python scripts/seed_mock_data.py --replace-existing --professores 100 --salas 45 --disciplinas 60 --alunos 1500 --timetables 520 --attendance-days 6
```
