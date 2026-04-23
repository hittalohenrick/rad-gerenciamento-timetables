# Documento de Planejamento de Requisitos

## Sistema de Gerenciamento de Timetables

- **Disciplina:** Desenvolvimento Rápido de Aplicações em Python (RAD)
- **Professor:** Elton Silva
- **Semestre:** 2026_01
- **Versão do documento:** final (23/04/2026)

## 1. Definição do problema

A gestão de turmas feita manualmente (planilhas e comunicação informal) gera conflitos de horário, inconsistência de matrícula e baixa rastreabilidade de presença.

## 2. Objetivo

Entregar uma aplicação web para gestão acadêmica com:

- autenticação por perfil (`admin` e `professor`);
- CRUD das entidades acadêmicas;
- alocações com validações de integridade;
- chamada por professor com regras de data.

## 3. Requisitos funcionais

### RF01 - Autenticação e acesso

- login com `username` e senha;
- redirecionamento por perfil;
- bloqueio de rotas administrativas para não-admin.

### RF02 - CRUD de salas

- cadastrar/listar/editar/excluir;
- validar nome e capacidade.

### RF03 - CRUD de disciplinas

- cadastrar/listar/editar/excluir;
- garantir código único.

### RF04 - CRUD de professores

- cadastrar/listar/editar/excluir professor;
- usar login (`username`) e senha;
- reset administrativo de senha para valor padrão.

### RF05 - CRUD de alunos

- cadastrar/listar/editar/excluir;
- matrícula única por aluno.

### RF06 - CRUD de turmas (timetable)

- dia, hora início/fim, sala, professor e disciplina;
- bloquear conflitos de sala e professor;
- bloquear intervalo inválido (`hora_inicio >= hora_fim`).

### RF07 - Matrícula de alunos em turmas

- vincular aluno a turma;
- impedir duplicidade da mesma matrícula na mesma turma;
- impedir conflito de horário do aluno;
- respeitar capacidade da sala.

### RF08 - Chamada por professor

- registrar presença por turma e data;
- impedir data futura;
- exigir dia da semana coerente com a turma;
- atualizar chamada sem duplicar registros.

### RF09 - Gestão de senha

- troca de senha do usuário autenticado;
- validação mínima de senha no formulário.

## 4. Requisitos não funcionais

### RNF01 - Stack

- Python + Flask;
- SQLite + SQLAlchemy;
- Alembic para migrações.

### RNF02 - Integridade

- chaves estrangeiras e constraints de unicidade;
- tratamento de exceções de integridade no backend.

### RNF03 - Usabilidade

- interface web responsiva;
- navegação por perfil;
- feedback visual de validações e operações.

### RNF04 - Segurança

- senha com hash;
- proteção de rotas com autenticação/autorização;
- operações destrutivas via `POST` + CSRF.

### RNF05 - Qualidade

- testes unitários/integrados com `pytest`;
- testes E2E com Playwright.

## 5. Ferramentas escolhidas

- Python 3.12
- Flask, Flask-Login, Flask-WTF
- SQLAlchemy, Flask-Migrate
- SQLite
- Jinja + Bootstrap + CSS/JS próprios
- pytest + Playwright
- Git

## 6. Modelo de dados inicial

Entidades centrais:

- `user`, `sala`, `disciplina`, `timetable`, `aluno`, `matricula`, `presenca`.

Relações principais:

- `sala (1) -> (N) timetable`
- `user/professor (1) -> (N) timetable`
- `disciplina (1) -> (N) timetable`
- `aluno (1) -> (N) matricula`
- `timetable (1) -> (N) matricula`
- `aluno (1) -> (N) presenca`
- `timetable (1) -> (N) presenca`

## 7. Critérios de aceite da fase

- requisitos funcionais e não funcionais claros;
- tecnologia aderente ao escopo da disciplina;
- modelo de dados suficiente para CRUD + regras de negócio.
