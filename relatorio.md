# Relatorio do Projeto - Sistema de Gerenciamento de TimeTables

## 1. Informacoes Gerais

- **Nome do Projeto:** Sistema de Gerenciamento de TimeTables
- **Equipe:** Hittalo (ajustar caso haja outros integrantes)
- **Disciplina:** Desenvolvimento Rapido de Aplicacoes em Python (RAD)
- **Professor:** Elton Silva
- **Data de Inicio:** 23/03/2026
- **Data de Conclusao:** 06/04/2026

## 2. Introducao

### Objetivo do Projeto

O projeto tem como objetivo apoiar a gestao academica de horarios de aula, permitindo que um administrador cadastre e mantenha salas, professores, disciplinas e alocacoes (timetables). O sistema resolve o problema de organizacao manual de grade horaria, reduzindo conflitos de sala e professor por meio de validacoes automaticas.

## 3. Planejamento de Requisitos (Fase 1 do RAD)

### Requisitos Funcionais

1. **RF01 - Autenticacao de Administrador:** login para acesso as areas administrativas.
2. **RF02 - Gerenciamento de Salas:** cadastrar, listar, editar e excluir salas com nome e capacidade.
3. **RF03 - Gerenciamento de Professores:** cadastrar, listar, editar e excluir professores com nome e email unico.
4. **RF04 - Gerenciamento de Disciplinas:** cadastrar, listar, editar e excluir disciplinas com codigo gerado automaticamente.
5. **RF05 - Gerenciamento de Alocacoes:** cadastrar, listar, editar e excluir alocacoes contendo dia, hora inicio/fim, sala, professor e disciplina.
6. **Regra de Negocio Critica:** bloquear sobreposicao de horario para a mesma sala e para o mesmo professor.

### Requisitos Nao Funcionais

1. **Persistencia:** uso de banco relacional SQLite.
2. **Integridade:** chaves estrangeiras ativas e verificadas no SQLite (`PRAGMA foreign_keys=ON`).
3. **Interface:** aplicacao web responsiva, com layout baseado em Bootstrap.
4. **Confiabilidade:** validacoes no formulario e tratamento de erros de integridade no backend.

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

### Modelo Inicial do Banco de Dados

- `User (id, username, email, password_hash, role)`
- `Sala (id, nome, capacidade)`
- `Disciplina (id, nome, codigo)`
- `Timetable (id, dia, hora_inicio, hora_fim, sala_id, professor_id, disciplina_id)`

Relacionamentos:

- `Sala 1:N Timetable`
- `User (professor) 1:N Timetable`
- `Disciplina 1:N Timetable`

## 4. Design do Usuario (Fase 2 do RAD)

### Prototipos de Interface

Os prototipos foram evoluidos diretamente em telas HTML/Jinja (abordagem iterativa RAD), com as principais views:

- Tela de login
- Dashboard administrativo
- CRUD de salas
- CRUD de professores
- CRUD de disciplinas
- CRUD de alocacoes
- Dashboard do professor (somente seus horarios)

### Estrutura de Navegacao

1. Login
2. Redirecionamento por papel:
   - Admin -> Dashboard administrativo
   - Professor -> Dashboard de horarios pessoais
3. Menu administrativo para navegar entre entidades e alocacoes

### Discussoes de Design

- Foi priorizada navegacao simples para operacoes CRUD.
- O dashboard administrativo concentra atalhos para todas as entidades.
- Mensagens de feedback (flash) foram mantidas em todas as operacoes.
- Formularios foram ajustados para exibir erros de validacao em tela.

### Decisoes Tomadas

1. Uso de Bootstrap para acelerar iteracoes de interface.
2. Uso de SelectField para horarios e relacionamentos (sala/professor/disciplina).
3. Restricao de acesso por papel (`admin` e `professor`).
4. Bloqueio de exclusao de entidades com alocacoes vinculadas para preservar integridade.

## 5. Construcao (Fase 3 do RAD)

### Desenvolvimento

A construcao foi realizada em incrementos:

1. Estrutura base Flask + autenticacao.
2. Modelos relacionais e migracoes.
3. CRUD de salas, professores e disciplinas.
4. CRUD de alocacoes com validacoes de negocio.
5. Refino final com validacoes adicionais e tratamento de erros.

### Implementacoes Relevantes da Versao Final

1. **Validacoes de formulario fortalecidas:** tamanho minimo/maximo, capacidade minima, validacao de intervalo de horario.
2. **Conflitos de alocacao corrigidos:** bloqueio por sobreposicao parcial ou total para mesma sala e mesmo professor.
3. **Tratamento de integridade:** controle de duplicidade (nome/email/cadastro) e rollback em `IntegrityError`.
4. **Integridade referencial no SQLite:** habilitacao explicita de `foreign_keys`.
5. **Templates atualizados:** exibicao dos erros de validacao para o usuario.

### Distribuicao das Tarefas

- Modelagem e backend (Flask/ORM): Hittalo
- Interface (templates/CSS): Hittalo
- Testes automatizados: Hittalo
- Documentacao e relatorio: Hittalo

(Atualizar esta secao caso haja divisao entre mais integrantes.)

### Integracao Continua

- Versionamento com Git
- Evolucao incremental por ajustes de requisitos
- Validacao frequente com testes automatizados (`pytest`)

## 6. Transicao (Fase 4 do RAD)

### Testes Realizados

Foram executados testes automatizados para validar regras criticas:

1. Redirecionamento quando usuario nao autenticado acessa a raiz.
2. Disponibilidade da tela de login.
3. Deteccao de sobreposicao de horario para professor.
4. Deteccao de sobreposicao de horario para sala.
5. Validacao de horario invalido (inicio >= fim).
6. Bloqueio de exclusao de sala com alocacoes vinculadas.
7. Bloqueio de cadastro de professor com email duplicado.

Resultado da execucao: **7 testes aprovados**.

### Feedback do Usuario

- Necessidade de alinhar completamente as regras do trabalho final.
- Necessidade de reforcar validacoes e tratamento de erros.
- Necessidade de consolidar o relatorio final no modelo exigido.

### Implantacao

Implantacao local para ambiente academico:

1. Instalar dependencias (`pip install -r requirements.txt`).
2. Aplicar migracoes (`flask db upgrade`).
3. Criar usuario admin (`python create_admin.py`).
4. Executar aplicacao (`python run.py`).

`Deploy` em nuvem nao foi exigido nesta etapa.

## 7. Conclusoes

### Resultados Alcancados

O sistema atende os requisitos obrigatorios do trabalho:

- Framework Python utilizado (Flask)
- Banco relacional (SQLite)
- CRUD completo
- Tabelas relacionadas com chaves estrangeiras
- Validacao de dados e regras de negocio
- Documentacao em formato RAD

### Aprendizados

1. Importancia da validacao de negocio alem das constraints do banco.
2. Necessidade de tratamento de excecoes para melhorar robustez.
3. Ganho de produtividade com ciclos curtos e iterativos da metodologia RAD.
4. Beneficio de testes automatizados para garantir regressao controlada.

### Proximos Passos (Opcional)

1. Implementar paginacao e filtros avancados nos CRUDs.
2. Adicionar exportacao de horarios (CSV/PDF).
3. Criar fluxo de troca de senha para professores.
4. Adicionar logs de auditoria para operacoes administrativas.

## 8. Anexos

### Codigo Fonte

- Repositorio local: `rad-gerenciamento-timetables`
- Link remoto: adicionar URL do GitHub/GitLab quando publicado.

### Documentacao Tecnica

- `docs/Planejamento de Requisitos.md`
- `docs/TRABALHO FINAL_CRITERIOS.md`
- `docs/Modelo de Relatorio para o Projeto.md`

## Formato Geral

Para entrega academica em documento editor:

- Fonte Arial ou Calibri, tamanho 12
- Espacamento 1.5
- Alinhamento justificado
- Citacoes/referencias no padrao ABNT ou APA
