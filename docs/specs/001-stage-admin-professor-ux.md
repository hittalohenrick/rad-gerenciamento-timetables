# Spec 001 - Etapa 1 UX (Admin + Professor)

## Objetivo
Reduzir desorganizacao operacional e melhorar clareza de decisao nas telas principais.

## Escopo da Etapa
- Navegacao lateral reorganizada por dominio.
- Novo painel administrativo orientado a fluxo e pendencias.
- Painel do professor com agenda semanal e atalhos para chamada.
- Banco reiniciado para ambiente limpo de demonstracao/desenvolvimento.

## Fora de Escopo (nesta etapa)
- Novo motor de alocacao automatica de professores.
- Reescrita total de CRUDs de entidade.
- Controle de permissoes avancado alem de admin/professor.

## User Stories
1. Como admin, quero ver pendencias do processo academico em um painel unico para priorizar minha operacao.
2. Como admin, quero abrir diretamente as telas corretas para resolver gargalos.
3. Como professor, quero enxergar minhas aulas por dia e acessar a chamada em um clique.

## Criterios de Aceite
1. Sidebar do admin possui agrupamentos por contexto (`Painel`, `Estrutura Academica`, `Oferta e Alocacao`).
2. Dashboard admin mostra:
- maturidade de quadro por turma
- quantidade de horarios sem professor
- quantidade de turmas sem quadro
- quantidade de turmas sem alunos
3. Dashboard admin lista alocacoes sem professor com CTA `Alocar Professor`.
4. Dashboard professor mostra:
- KPI semanal (aulas, turmas, disciplinas, alunos atendidos)
- blocos por dia da semana
- CTA para chamada em cada aula
5. Alocacao docente ocorre em tela dedicada por aula, exibindo somente professores aptos e disponiveis.
6. Sistema bloqueia alocacao docente quando a grade da turma estiver incompleta.
7. Layout responsivo em desktop e mobile sem quebra visual severa.

## Validacao
- Testes automatizados do projeto continuam passando.
- Validacao manual:
1. Login admin e professor
2. Navegacao principal
3. Fluxos de alocacao e chamada
