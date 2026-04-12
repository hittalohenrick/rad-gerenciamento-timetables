# Documento de Design do Usuario (Fase 2 RAD)

## Projeto
Sistema de Gerenciamento de Timetables

## 1. Objetivo

Registrar as decisoes de UX/UI e o fluxo de navegacao do sistema, garantindo coerencia com os requisitos funcionais definidos na Fase 1.

## 2. Estrutura de Navegacao

### 2.1 Fluxo do Administrador
1. Login (`/login`)
2. Dashboard (`/admin`)
3. Modulos de gerenciamento:
- Salas (`/salas`)
- Professores (`/professores`)
- Disciplinas (`/disciplinas`)
- Alunos (`/alunos`)
- Alocacao de Alunos (`/matriculas`)
- Horarios (`/horarios`)

### 2.2 Fluxo do Professor
1. Login (`/login`)
2. Dashboard do professor (`/professor`)
3. Chamada por turma (`/professor/turma/<id>/chamada`)

## 3. Prototipos de Tela (implementados)

- **Tela de Login:** autenticacao com usuario e senha.
- **Dashboard Administrativo:** visao consolidada de indicadores e atalhos.
- **Telas CRUD:** listagem + formulario para Salas, Professores, Disciplinas e Alunos.
- **Tela de Alocacoes de Timetable:** administracao da grade.
- **Tela de Alocacao de Alunos:** vinculo aluno-turma com busca.
- **Dashboard do Professor:** turmas atribuidas e acesso rapido a chamada.
- **Tela de Chamada:** filtro de alunos, marcacao em lote e resumo de presenca.

## 4. Decisoes de Interface

1. **Separacao por perfil:** menus e permissoes diferentes para `admin` e `professor`.
2. **Tema visual consistente:** paleta escura com destaque azul e acento turquesa (regra 60/30/10).
3. **Acoes por contexto:** botoes padronizados por tipo de acao (`primaria`, `editar`, `destrutiva`).
4. **Feedback imediato:** mensagens de sucesso/erro em todas as operacoes.
5. **Formularios com validacao visivel:** erros apresentados no proprio campo.

## 5. Ajustes Realizados Apos Discussao e Testes

1. **Alocacao com pesquisa:** seletores de sala/professor/disciplina/aluno/turma com busca textual.
2. **Chamada aprimorada:**
- busca por aluno;
- marcar/desmarcar visiveis;
- resumo dinamico (total/presentes/faltas);
- bloqueios por data invalida.
3. **Refino de consistencia visual:**
- cor do botao de editar padronizada com o tema;
- alinhamento das acoes em tabela;
- correcao de autofill em campos de senha no tema escuro.

## 6. Justificativa das Escolhas

As escolhas priorizam rapidez de uso, legibilidade e previsibilidade, alinhadas com a metodologia RAD:

- ciclos curtos de feedback visual;
- alteracoes incrementais com baixo custo de retrabalho;
- foco em entregar funcionalidade com interface clara para demonstracao academica.

## 7. Evidencias Recomendadas para Apresentacao

Para a entrega final (relatorio em PDF/DOCX), anexar prints de:

1. Login
2. Dashboard admin
3. CRUD de professores
4. Alocacao de timetable
5. Alocacao de alunos
6. Dashboard professor
7. Chamada da turma
