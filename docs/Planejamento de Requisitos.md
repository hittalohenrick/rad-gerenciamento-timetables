# Documento de Planejamento de Requisitos

## Sistema de Gerenciamento de Timetables

- **Disciplina:** Desenvolvimento Rapido de Aplicacoes em Python (RAD)
- **Professor:** Elton Silva
- **Semestre:** 2026_01
- **Data da versao:** 12/04/2026

## 1. Definicao do Problema

A grade academica costuma ser controlada de forma manual (planilhas, mensagens e comunicacoes isoladas), o que causa conflitos de horario entre sala/professor, retrabalho de alocacao e pouco controle de presenca.

## 2. Objetivo do Sistema

Desenvolver uma aplicacao web para administrar turmas e horarios de forma centralizada, com:

- autenticacao por perfil (`admin` e `professor`);
- cadastro e manutencao de entidades academicas;
- alocacao de turmas sem conflitos de agenda;
- alocacao de alunos em turmas;
- registro de chamada por professor.

## 3. Escopo Funcional (Requisitos Funcionais)

### RF01 - Autenticacao e controle de acesso
- Login com usuario e senha.
- Redirecionamento por perfil.
- Restricao de rotas administrativas para perfil `admin`.

### RF02 - Gerenciamento de salas (CRUD)
- Cadastrar, listar, editar e excluir salas.
- Validar nome e capacidade.

### RF03 - Gerenciamento de disciplinas (CRUD)
- Cadastrar, listar, editar e excluir disciplinas.
- Gerar codigo unico da disciplina.

### RF04 - Gerenciamento de professores (CRUD)
- Cadastrar, listar, editar e excluir professores.
- Definir login, email e senha.
- Permitir reset de senha para um valor padrao.

### RF05 - Gerenciamento de alunos (CRUD)
- Cadastrar, listar, editar e excluir alunos.
- Garantir matricula unica.

### RF06 - Gerenciamento de alocacoes (timetable) (CRUD)
- Cadastrar, listar, editar e excluir turmas (dia, horario, sala, professor, disciplina).
- Bloquear conflitos de horario por sala e por professor.
- Bloquear faixa de horario invalida (`hora_inicio >= hora_fim`).

### RF07 - Alocacao de alunos em turmas
- Vincular aluno a turma.
- Bloquear duplicidade da mesma matricula na mesma turma.
- Bloquear conflito de horario do aluno.
- Respeitar capacidade maxima da sala.

### RF08 - Chamada por professor
- Professor registra presenca por turma e por data.
- Bloquear chamada em data futura.
- Bloquear chamada em dia da semana diferente do dia da turma.
- Atualizar chamada da mesma data sem duplicar registros.

### RF09 - Seguranca de senha
- Validar politica minima de senha (tamanho minimo).
- Permitir troca de senha do usuario autenticado.

## 4. Requisitos Nao Funcionais

### RNF01 - Tecnologia
- Backend em Python com Flask.
- Persistencia com banco relacional SQLite.
- ORM com SQLAlchemy e migracoes Alembic.

### RNF02 - Integridade de dados
- Uso de chaves estrangeiras e constraints de unicidade.
- Tratamento de excecoes de integridade no backend.

### RNF03 - Usabilidade
- Interface web responsiva.
- Fluxo de navegacao separado por perfil.
- Formularios com feedback de validacao.

### RNF04 - Seguranca
- Senhas armazenadas com hash.
- Rotas sensiveis protegidas por autenticacao e autorizacao.
- Operacoes destrutivas via `POST` com CSRF.

### RNF05 - Qualidade
- Testes automatizados de unidade/integracao (pytest) e E2E (Playwright).

## 5. Ferramentas e Tecnologias Escolhidas

- **Linguagem:** Python 3.12
- **Framework Web:** Flask
- **Banco de Dados:** SQLite
- **ORM:** Flask-SQLAlchemy
- **Migracoes:** Flask-Migrate / Alembic
- **Autenticacao:** Flask-Login
- **Validacao de formularios:** Flask-WTF / WTForms
- **Frontend:** Jinja2 + Bootstrap + CSS customizado
- **Testes:** pytest + Playwright
- **Versionamento:** Git

## 6. Modelo Inicial do Banco de Dados

### Entidades principais
- `user` (usuarios administrativos e professores)
- `sala`
- `disciplina`
- `timetable`
- `aluno`
- `matricula`
- `presenca`

### Relacionamentos iniciais
- `sala (1) -> (N) timetable`
- `user/professor (1) -> (N) timetable`
- `disciplina (1) -> (N) timetable`
- `aluno (1) -> (N) matricula`
- `timetable (1) -> (N) matricula`
- `aluno (1) -> (N) presenca`
- `timetable (1) -> (N) presenca`

### Regras iniciais de consistencia
- Unicidade de login e email do usuario.
- Unicidade de matricula de aluno.
- Unicidade de alocacao por sala e por professor no mesmo intervalo.
- Unicidade de presenca por `data + aluno + turma`.

## 7. Criterios de Aceite da Fase de Planejamento

- Requisitos funcionais e nao funcionais descritos de forma clara.
- Tecnologias justificadas e aderentes ao escopo.
- Modelo de dados inicial com relacionamentos suficientes para suportar CRUD e regras de negocio.
