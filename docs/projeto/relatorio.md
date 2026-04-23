# Relatório do Projeto - Sistema de Gerenciamento de Timetables

Versão final: 23/04/2026

## 1. Informações gerais

- Projeto: Sistema de Gerenciamento de Timetables
- Disciplina: Desenvolvimento Rápido de Aplicações em Python (RAD)
- Tipo: projeto individual
- Stack: Flask + SQLAlchemy + SQLite + Jinja + pytest + Playwright

## 2. Introdução

O projeto resolve o problema de gestão manual de grade e presença, centralizando:

- cadastro da estrutura acadêmica;
- oferta de turmas com validações;
- matrícula de alunos com controle de capacidade;
- chamada por professor com regras de data.

## 3. Fase 1 (Planejamento)

- escopo funcional e não funcional definido;
- tecnologia escolhida e justificada;
- modelo relacional inicial aprovado.

Documento de apoio: `docs/Planejamento de Requisitos.md`.

## 4. Fase 2 (Design do usuário)

- fluxos separados por perfil (`admin` e `professor`);
- telas de CRUD, alocação e chamada;
- refinamentos de usabilidade orientados por testes.

Documento de apoio: `docs/projeto/documento_prototipo_interface.md`.

## 5. Fase 3 (Construção)

Implementações concluídas:

- backend modular (`auth`, `admin`, `professor`, `helpers`);
- modelagem relacional completa (`user`, `sala`, `disciplina`, `timetable`, `aluno`, `matricula`, `presenca`);
- validações de regra de negócio (conflito, capacidade, datas);
- interface integrada e responsiva.

Documento de apoio: `docs/projeto/documento_modelagem.md`.

## 6. Fase 4 (Transição e validação)

## 6.1 Testes executados

- Unitário/integração (`pytest`): **21 passed**
- E2E (Playwright): **5 passed**

## 6.2 Evidências

- vídeo funcional completo: `docs/evidencias/video_teste_funcionalidades.webm`
- relatório E2E: `docs/evidencias/playwright-report/index.html`

## 6.3 Limpeza e simplificação

- fluxo de professor simplificado para login por `username`;
- remoção de excesso visual e padronização de formulários;
- documentação consolidada e atualizada.

## 7. Conclusão

O sistema está pronto para apresentação final, com:

- funcionalidades centrais completas;
- regras de negócio consistentes;
- testes automatizados cobrindo backend e frontend;
- documentação técnica final consolidada.

## 8. Referências internas

- `README.md`
- `docs/documentacao_geral_final.md`
- `docs/evidencias_testes.md`
