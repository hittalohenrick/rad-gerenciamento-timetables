# Relatorio do Projeto - Sistema de Gerenciamento de Timetables

## 1. Informacoes Gerais

- **Nome do Projeto:** Sistema de Gerenciamento de Timetables
- **Equipe:** Hittalo (projeto individual nesta entrega)
- **Disciplina:** Desenvolvimento Rapido de Aplicacoes em Python (RAD)
- **Professor:** Elton Silva
- **Semestre:** 2026_01
- **Data de Inicio:** 23/03/2026
- **Data de Conclusao da versao atual:** 12/04/2026

## 2. Introducao

### Objetivo do Projeto

Desenvolver um sistema web para gestao academica com foco em organizacao de turmas, horarios e presencas, reduzindo conflitos de agenda e centralizando o controle administrativo e docente.

### Problema que a aplicacao resolve

O controle manual de grade e chamada gera inconsistencias frequentes (choque de horario, duplicidade de alocacao e dificuldade de rastreio). O sistema digitaliza esse fluxo com validacoes automaticas e trilha de dados persistida em banco relacional.

## 3. Planejamento de Requisitos (Fase 1 do RAD)

### Requisitos Funcionais

1. Login e controle de acesso por perfil (`admin` e `professor`).
2. CRUD completo de salas.
3. CRUD completo de disciplinas.
4. CRUD completo de professores (com senha e reset administrativo).
5. CRUD completo de alunos.
6. CRUD completo de alocacoes (timetable).
7. Alocacao de alunos em turmas.
8. Chamada da turma por professor e por data.

### Requisitos Nao Funcionais

1. Backend Python com Flask.
2. Banco relacional SQLite com SQLAlchemy.
3. Migracoes versionadas com Alembic.
4. Interface responsiva e objetiva para uso em aula/apresentacao.
5. Validacoes de dados no formulario e nas regras de negocio.
6. Testes automatizados para reduzir regressao.

### Ferramentas Utilizadas

- Python 3.12
- Flask, Flask-Login, Flask-WTF
- Flask-SQLAlchemy, Flask-Migrate (Alembic)
- SQLite
- Bootstrap + CSS customizado
- pytest e Playwright
- Git

### Modelo inicial do banco

Modelo iniciado com entidades centrais (`user`, `sala`, `disciplina`, `timetable`) e evoluido para suportar alunos, matriculas e presencas (`aluno`, `matricula`, `presenca`), mantendo relacionamentos 1:N e regras de unicidade.

## 4. Design do Usuario (Fase 2 do RAD)

### Prototipos de Interface

Foram definidos e implementados prototipos funcionais para:

- login;
- dashboard administrativo;
- CRUD de salas, professores, disciplinas e alunos;
- alocacao de timetable;
- alocacao de alunos;
- dashboard do professor;
- chamada da turma.

### Discussao de Design

Os ajustes foram conduzidos por iteracao curta, com foco em apresentacao clara para avaliacao da disciplina:

- simplificacao de layout e hierarquia visual;
- padronizacao de botoes por tipo de acao;
- melhoria de leitura de tabelas extensas;
- refinamento da tela de chamada para operacao em lote.

### Decisoes Tomadas

1. Navegacao separada por perfil (admin/professor).
2. Tema visual unico e consistente.
3. Busca em campos de alocacao para reduzir tempo de operacao.
4. Mensagens de feedback em todas as acoes criticas.

## 5. Construcao (Fase 3 do RAD)

### Desenvolvimento

A construcao foi incremental:

1. autenticacao e estrutura base Flask;
2. modelagem ORM e migracoes;
3. CRUDs principais;
4. regras de conflito de horario e integridade;
5. fluxo de matricula de alunos;
6. fluxo de chamada do professor;
7. testes automatizados e refinamento de UX/UI.

### Distribuicao das Tarefas

Projeto individual nesta versao, com distribuicao por frente tecnica:

- backend e modelagem de dados;
- frontend (templates/CSS);
- testes automatizados;
- documentacao tecnica.

### Integracao Continua

- Uso de Git para versionamento incremental.
- Validacao recorrente com `pytest` e Playwright a cada ajuste relevante.
- Ajustes de UI e regras de negocio orientados por feedback dos testes.

## 6. Transicao (Fase 4 do RAD)

### Testes Realizados

- **pytest:** 21 testes aprovados (autenticacao, autorizacao, conflitos, matriculas, presenca e regras de senha simples).
- **Playwright E2E:** 4 testes aprovados (fluxo admin e fluxo professor/chamada).

### Feedback do Usuario

Principais ajustes apos feedback:

1. pesquisa na alocacao para selecao de entidades;
2. melhoria do fluxo de chamada (busca + marcacao em lote + validacoes de data);
3. correcao de consistencia visual (acoes de tabela e campos com autofill).

### Implantacao

Deploy nao obrigatorio pela disciplina. Execucao local:

1. `python3 -m venv .venv`
2. `. .venv/bin/activate`
3. `pip install -r requirements.txt`
4. `export FLASK_APP=run.py`
5. `flask db upgrade`
6. `python create_admin.py`
7. `python run.py`

## 7. Conclusoes

### Resultados Alcancados

O projeto atende aos criterios obrigatorios:

- framework Python aplicado;
- banco relacional integrado;
- CRUD completo;
- tabelas relacionadas (mais de 2);
- validacao de dados e regras de negocio;
- documentacao organizada por fases RAD.

### Aprendizados

1. Modelagem de dados bem definida reduz retrabalho.
2. Regras de negocio no backend complementam constraints do banco.
3. Testes automatizados aceleram correcao com seguranca.
4. Pequenos ciclos de UX melhoram muito a apresentacao final.

### Proximos Passos (Opcional)

1. Exportacao de relatorios de presenca (CSV/PDF).
2. Dashboards com metricas por turma/disciplina.
3. Auditoria de alteracoes administrativas.

## 8. Anexos

### Codigo Fonte

- Repositorio local: `rad-gerenciamento-timetables`
- Link remoto: adicionar URL do repositorio publico (quando publicado)

### Documentacao Tecnica

- `docs/Planejamento de Requisitos.md`
- `docs/projeto/documento_modelagem.md`
- `docs/projeto/documento_prototipo_interface.md`
- `docs/TRABALHO FINAL_CRITERIOS.md`
- `docs/Modelo de Relatorio para o Projeto.md`
