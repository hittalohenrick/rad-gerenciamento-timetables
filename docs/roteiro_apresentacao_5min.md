# Roteiro de Apresentação Oral (5 minutos)

## 0:00 - 0:30 | Abertura

Bom dia/boa tarde. Este projeto é o **Sistema de Gerenciamento de Timetables**, desenvolvido na disciplina de **Desenvolvimento Rápido de Aplicações em Python (RAD)**.

O objetivo foi resolver um problema real de gestão acadêmica: conflitos de horário, alocações inconsistentes e dificuldade no controle de presença quando tudo é feito manualmente.

## 0:30 - 1:15 | Problema e objetivo

Antes do sistema, a operação dependia de planilhas e conferência manual.

Isso gerava:

- conflito de sala e professor no mesmo horário;
- matrícula de aluno em turmas sobrepostas;
- retrabalho para ajuste de grade;
- baixa rastreabilidade da chamada.

O objetivo do sistema foi centralizar esse processo com regras automáticas de validação.

## 1:15 - 2:00 | Arquitetura e tecnologias

A solução foi implementada em **Python + Flask**, com arquitetura monolítica modular.

- **Banco:** SQLite, com ORM SQLAlchemy.
- **Migrações:** Alembic/Flask-Migrate.
- **Autenticação:** Flask-Login.
- **Validação de formulários:** Flask-WTF/WTForms.
- **Interface:** Jinja + Bootstrap + CSS/JS customizados.
- **Qualidade:** testes unitários com pytest e E2E com Playwright.

A escolha dessas ferramentas foi guiada por rapidez de entrega, simplicidade de manutenção e aderência à metodologia RAD.

## 2:00 - 3:30 | Demonstração funcional (o que mostrar na tela)

1. **Login** com dois perfis: admin e professor.
2. **Admin dashboard** com visão geral.
3. CRUDs principais: salas, disciplinas, professores e alunos.
4. **Nova alocação de turma** com validação de conflito.
5. **Matrícula de aluno** com bloqueio por capacidade e choque de horário.
6. Login como **professor**.
7. Tela **Minhas Turmas**.
8. **Chamada da turma**: marcar presença, validar data e salvar histórico.

## 3:30 - 4:20 | Regras de negócio e integridade

As principais regras implementadas foram:

- impedir sobreposição de horário para sala e professor;
- impedir matrícula duplicada do mesmo aluno na mesma turma;
- impedir matrícula quando a capacidade da sala é atingida;
- impedir chamada em data futura;
- exigir que a data da chamada corresponda ao dia da turma.

Além disso, o banco tem constraints para garantir integridade relacional.

## 4:20 - 4:45 | Testes e evidências

A solução foi validada com:

- **21 testes unitários/integrados (pytest)** aprovados;
- **5 testes E2E (Playwright)** aprovados.

Também foi gerado vídeo de execução ponta a ponta em:

- `docs/evidencias/video_teste_funcionalidades.webm`

## 4:45 - 5:00 | Encerramento

Como resultado, o sistema está funcional, testado e documentado.

Ele atende ao escopo da disciplina RAD com foco em clareza de arquitetura, regras de negócio consistentes e operação acadêmica real.

Obrigado.
