# Relatorio do Projeto - Sistema de Gerenciamento de Timetables

## 1. Informacoes Gerais

- **Nome do Projeto:** Sistema de Gerenciamento de Timetables
- **Equipe:** Hittalo (projeto individual nesta entrega)
- **Disciplina:** Desenvolvimento Rapido de Aplicacoes em Python (RAD)
- **Professor:** Elton Silva
- **Data de Inicio:** 23/03/2026
- **Data da Entrega (Fase atual):** 06/04/2026
- **Status da Entrega:** concluido para apresentacao de modelagem do banco e prototipo da interface

## 2. Introducao

### Objetivo do Projeto

Desenvolver um sistema web para organizacao de grade horaria escolar, permitindo cadastro e manutencao de salas, professores, disciplinas e alocacoes de aula, com validacoes para evitar conflitos de horario.

### Problema Resolvido

O projeto substitui controle manual de horarios por um fluxo digital com regras de consistencia, reduzindo choques de agenda entre professor e sala.

## 3. Planejamento de Requisitos (Fase 1 do RAD)

### Requisitos Funcionais

1. **RF01 - Autenticacao de usuarios:** login com controle de sessao.
2. **RF02 - Perfil administrador:** acesso a operacoes de cadastro e gerenciamento.
3. **RF03 - CRUD de salas:** criar, listar, editar e excluir salas.
4. **RF04 - CRUD de professores:** criar, listar, editar e excluir professores.
5. **RF05 - CRUD de disciplinas:** criar, listar, editar e excluir disciplinas.
6. **RF06 - CRUD de alocacoes (timetable):** criar, listar, editar e excluir alocacoes.
7. **RF07 - Cadastro de professores para alocacao:** professores sao mantidos como entidade de dominio para composicao da grade.

### Requisitos Nao Funcionais

1. **Persistencia relacional:** SQLite em ambiente local.
2. **Integridade de dados:** constraints de chave primaria, chave estrangeira e unicidade.
3. **Usabilidade:** interface web responsiva com Bootstrap.
4. **Confiabilidade:** validacao de formulario e tratamento de excecoes (`IntegrityError`).
5. **Qualidade:** testes automatizados para fluxos criticos.

### Ferramentas Utilizadas

- Python 3
- Flask
- Flask-SQLAlchemy
- Flask-Migrate (Alembic)
- Flask-Login
- Flask-WTF / WTForms
- SQLite
- pytest
- Git

### Modelagem do Banco de Dados (Entrega da Fase)

#### Entidades e Campos

| Tabela | Campos principais | Regras |
|---|---|---|
| `user` | `id`, `username`, `email`, `password_hash`, `role` | `username` e `email` unicos; `role` define permissao |
| `sala` | `id`, `nome`, `capacidade` | `capacidade` obrigatoria |
| `disciplina` | `id`, `nome`, `codigo` | `codigo` unico |
| `timetable` | `id`, `dia`, `hora_inicio`, `hora_fim`, `sala_id`, `professor_id`, `disciplina_id` | FKs para `sala`, `user`, `disciplina`; constraints de unicidade por faixa de horario |

#### Relacionamentos

- `Sala (1) -> (N) Timetable`
- `User (professor) (1) -> (N) Timetable`
- `Disciplina (1) -> (N) Timetable`

#### Regras de Integridade e Negocio

1. `timetable.sala_id` referencia `sala.id`.
2. `timetable.professor_id` referencia `user.id`.
3. `timetable.disciplina_id` referencia `disciplina.id`.
4. `UNIQUE (dia, hora_inicio, hora_fim, sala_id)` evita duplicidade exata de faixa na mesma sala.
5. `UNIQUE (dia, hora_inicio, hora_fim, professor_id)` evita duplicidade exata de faixa para o mesmo professor.
6. Validacao de sobreposicao de intervalos no backend bloqueia conflitos parciais e totais.

#### Modelo Relacional (Visao textual)

`user (id)` <- `timetable.professor_id` -> `timetable (id)` <- `timetable.sala_id` -> `sala (id)`  
`disciplina (id)` <- `timetable.disciplina_id`

## 4. Design do Usuario (Fase 2 do RAD)

### Prototipo da Interface (Entrega da Fase)

Os prototipos foram evoluidos diretamente em templates HTML/Jinja com Bootstrap, resultando nas telas abaixo:

1. **Login (`/login`)**
- Campos de usuario e senha.
- Feedback visual para erro de autenticacao.

2. **Dashboard administrativo (`/admin`)**
- Cards com indicadores (salas, professores, disciplinas e alocacoes).
- Atalhos para CRUD das entidades.
- Tabela consolidada de alocacoes com acoes de editar/deletar.

3. **CRUD de Salas (`/salas`, `/sala/new`, `/sala/edit/...`)**
- Listagem, cadastro e edicao.
- Bloqueio de exclusao quando existe alocacao vinculada.

4. **CRUD de Professores (`/professores`, `/professor/new`, `/professor/edit/...`)**
- Cadastro e manutencao de usuarios com papel `professor`.
- Validacao de duplicidade de usuario/email.

5. **CRUD de Disciplinas (`/disciplinas`, `/disciplina/new`, `/disciplina/edit/...`)**
- Cadastro com codigo unico gerado automaticamente.
- Controle de duplicidade por nome.

6. **Formulario de Alocacao (`/timetable/new`, `/timetable/edit/...`)**
- Selecao de dia, faixa de horario, sala, professor e disciplina.
- Validacao de horario invalido e conflito de agenda.

7. **Listagem de Horarios (`/horarios`)**
- Visao administrativa consolidada da grade.
- Acoes de edicao e exclusao de alocacoes.

### Estrutura de Navegacao

1. Usuario acessa login.
2. Sistema autentica somente usuario com papel `admin`.
3. Administrador navega por menu "Gerenciar" para manter entidades e alocacoes.

### Decisoes de Design

1. Navbar focada no fluxo administrativo (single-role).
2. Componentes padronizados com Bootstrap para acelerar iteracoes RAD.
3. Mensagens `flash` para cada acao (sucesso, aviso e erro).
4. Formularios com exibicao direta dos erros de validacao.
5. Exclusoes migradas para `POST` com protecao CSRF.
6. Layout responsivo com CSS proprio em `static/css/styles.css`.

## 5. Construcao (Fase 3 do RAD)

### Desenvolvimento

Implementacao feita em incrementos curtos:

1. Estrutura base Flask com autenticacao.
2. Modelagem ORM + migrations.
3. CRUD completo das entidades principais.
4. Regras de conflito de horario e integridade.
5. Refino da interface e mensagens de usuario.

### Distribuicao das Tarefas

- Modelagem do banco e backend: Hittalo
- Prototipo e implementacao de interface: Hittalo
- Testes automatizados: Hittalo
- Documentacao e relatorio: Hittalo

### Integracao Continua

- Versionamento com Git.
- Evolucao incremental de requisitos para implementacao.
- Validacao recorrente com testes (`pytest`).

## 6. Transicao (Fase 4 do RAD)

### Testes Realizados

Foram executados testes automatizados de autenticacao, validacao e integridade:

1. Redirecionamento para login quando nao autenticado.
2. Disponibilidade da tela de login.
3. Bloqueio de login para usuario nao-admin.
4. Bloqueio de conflito de horario para professor.
5. Bloqueio de conflito de horario para sala.
6. Validacao de faixa de horario invalida.
7. Bloqueio de exclusao de sala com alocacoes.
8. Exclusao administrativa aceita apenas `POST` (bloqueio de `GET`).
9. Bloqueio de cadastro de professor com email duplicado.

**Resultado atual:** 9 testes aprovados.

### Implantacao Local

1. `pip install -r requirements.txt`
2. `python -m flask db upgrade`
3. `python create_admin.py` (se necessario)
4. `python run.py`

## 7. Conclusoes

### Resultados Alcancados

O sistema atende os criterios principais do trabalho final:

- Framework Python aplicado (Flask).
- Banco relacional integrado (SQLite).
- CRUD funcional completo.
- Tabelas relacionadas com chaves estrangeiras.
- Validacoes de negocio e tratamento de erros.
- Relatorio estruturado no modelo RAD.

### Aprendizados

1. Modelagem relacional bem definida reduz retrabalho na fase de construcao.
2. Regras de negocio no backend complementam as constraints do banco.
3. Prototipos iterativos aceleram alinhamento de interface com requisitos.
4. Testes automatizados ajudam a manter estabilidade da aplicacao.

### Proximos Passos

1. Exportacao de horarios em CSV/PDF.
2. Filtros e pesquisa nas listagens administrativas.
3. Politica de troca de senha para professores.
4. Publicacao do repositorio remoto para anexar link final.

## 8. Anexos

### Codigo Fonte

- Repositorio local: `rad-gerenciamento-timetables`
- Link remoto: adicionar quando publicado.

### Documentacao Tecnica

- `docs/Planejamento de Requisitos.md`
- `docs/TRABALHO FINAL_CRITERIOS.md`
- `docs/Modelo de Relatorio para o Projeto.md`
