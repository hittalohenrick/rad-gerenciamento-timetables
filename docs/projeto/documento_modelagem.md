# Documento de Modelagem de Dados

Projeto: Sistema de Gerenciamento de Timetables

Versão: final (23/04/2026)

## 1. Objetivo

Definir o esquema relacional para suportar:

- gestão de usuários, salas, disciplinas e alunos;
- oferta de turmas (timetable);
- matrícula aluno-turma;
- registro de presença por data.

## 2. Entidades e atributos

## 2.1 `user`

- `id` (PK)
- `username` (UNIQUE, NOT NULL)
- `email` (UNIQUE, NOT NULL) **uso técnico interno**
- `password_hash` (NOT NULL)
- `role` (`admin` ou `professor`)

Observação: funcionalmente, o login do professor é por `username`.

## 2.2 `sala`

- `id` (PK)
- `nome` (NOT NULL)
- `capacidade` (NOT NULL)

## 2.3 `disciplina`

- `id` (PK)
- `nome` (NOT NULL)
- `codigo` (UNIQUE, NOT NULL)

## 2.4 `timetable`

- `id` (PK)
- `dia` (NOT NULL)
- `hora_inicio` (NOT NULL)
- `hora_fim` (NOT NULL)
- `sala_id` (FK -> `sala.id`, NOT NULL)
- `professor_id` (FK -> `user.id`, NOT NULL)
- `disciplina_id` (FK -> `disciplina.id`, NOT NULL)

Constraints de negócio:

- `UNIQUE (dia, hora_inicio, hora_fim, sala_id)`
- `UNIQUE (dia, hora_inicio, hora_fim, professor_id)`

## 2.5 `aluno`

- `id` (PK)
- `nome` (NOT NULL)
- `matricula` (UNIQUE, NOT NULL)
- `created_at` (NOT NULL)

## 2.6 `matricula`

- `id` (PK)
- `aluno_id` (FK -> `aluno.id`, NOT NULL)
- `timetable_id` (FK -> `timetable.id`, NOT NULL)
- `created_at` (NOT NULL)
- `UNIQUE (aluno_id, timetable_id)`

## 2.7 `presenca`

- `id` (PK)
- `data` (NOT NULL)
- `presente` (NOT NULL)
- `aluno_id` (FK -> `aluno.id`, NOT NULL)
- `timetable_id` (FK -> `timetable.id`, NOT NULL)
- `created_at` (NOT NULL)
- `UNIQUE (data, aluno_id, timetable_id)`

## 3. Relacionamentos

- `sala (1) -> (N) timetable`
- `user/professor (1) -> (N) timetable`
- `disciplina (1) -> (N) timetable`
- `aluno (1) -> (N) matricula`
- `timetable (1) -> (N) matricula`
- `aluno (1) -> (N) presenca`
- `timetable (1) -> (N) presenca`

## 4. Regras de integridade

1. unicidade de identidade: `user.username`, `aluno.matricula`, `disciplina.codigo`.
2. consistência de alocação: sem sobreposição de sala/professor no mesmo intervalo.
3. consistência de matrícula: aluno não pode repetir matrícula na mesma turma.
4. consistência de presença: um registro por aluno/turma/data.

## 5. Regras de negócio no backend

- bloqueio de conflito de horário (sala, professor e aluno);
- bloqueio por capacidade da sala;
- chamada não permite data futura;
- chamada exige dia da semana compatível com a turma.

## 6. Conclusão

A modelagem atende ao escopo RAD com base relacional íntegra, suporte a CRUD completo e regras essenciais da operação acadêmica.
