# Memorial Técnico - Sistema de Gerenciamento de Timetables

Versão final: 23/04/2026

## 1. Identificação

- Projeto: Sistema de Gerenciamento de Timetables
- Disciplina: Desenvolvimento Rápido de Aplicações em Python (RAD)
- Linguagem principal: Python
- Arquitetura: monolito modular em Flask

## 2. Visão do problema

A operação acadêmica em planilhas tende a produzir inconsistências de agenda e baixa rastreabilidade.

Riscos típicos:

- choque de horário entre professor e sala;
- matrícula de aluno em turmas sobrepostas;
- dificuldade para auditoria de presença.

## 3. Objetivo técnico

Construir uma aplicação web com regras explícitas de integridade para:

- gerir estrutura acadêmica (salas, disciplinas, professores, alunos);
- organizar oferta de turmas;
- matricular alunos com validações;
- registrar presença por professor e data.

## 4. Abordagem RAD aplicada

## 4.1 Planejamento

Definição de escopo, requisitos e modelo de dados inicial.

## 4.2 Design de usuário

Fluxos separados por perfil e telas orientadas à operação diária.

## 4.3 Construção

Implementação incremental por módulos, com validações de negócio no backend.

## 4.4 Transição

Testes automatizados, ajustes de UX e consolidação documental final.

## 5. Arquitetura implementada

Camadas principais:

1. apresentação (`templates/`, `static/`)
2. aplicação (`app/routes/`)
3. domínio e validação (`app/models.py`, `app/forms.py`)
4. persistência e evolução de schema (`migrations/`)
5. qualidade (`tests/`)

## 6. Entidades e regras

Entidades:

- `User`, `Sala`, `Disciplina`, `Timetable`, `Aluno`, `Matricula`, `Presenca`

Regras críticas:

- sem sobreposição de sala/professor no mesmo horário;
- sem matrícula duplicada do aluno na mesma turma;
- capacidade da sala respeitada;
- chamada sem data futura e no dia correto da turma.

## 7. Segurança e acesso

- autenticação por `username` e senha;
- autorização por perfil (`admin` e `professor`);
- senha armazenada com hash;
- rotas sensíveis protegidas por sessão.

## 8. Estratégia de testes

## 8.1 Backend

`pytest` cobrindo regras de negócio e fluxos principais.

Resultado final:

- **21 testes aprovados**.

## 8.2 E2E

Playwright cobrindo:

- fluxo admin;
- fluxo professor;
- fluxo ponta a ponta completo em teste único.

Resultado final:

- **5 testes aprovados**.

## 9. Evidências de validação

- vídeo funcional completo: `docs/evidencias/video_teste_funcionalidades.webm`
- relatório E2E: `docs/evidencias/playwright-report/index.html`
- evidências resumidas: `docs/evidencias_testes.md`

## 10. Decisões de simplificação final

- remoção de excesso visual e foco em legibilidade;
- cadastro/edição de professor simplificado para login + senha;
- manutenção de campo de e-mail apenas para compatibilidade técnica de modelo;
- documentação consolidada e atualizada.

## 11. Resultado final

O sistema está funcional para apresentação e avaliação, com:

- escopo acadêmico implementado;
- regras críticas protegidas por código e banco;
- evidência objetiva de qualidade via testes automáticos;
- documentação final para sustentação técnica.

## 12. Referências internas

- `README.md`
- `docs/README.md`
- `docs/documentacao_geral_final.md`
- `docs/projeto/relatorio.md`
