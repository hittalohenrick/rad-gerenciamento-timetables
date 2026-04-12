# Documento de Modelagem de Dados

## Projeto
Sistema de Gerenciamento de Timetables

## 1. Objetivo da Modelagem

Definir a estrutura relacional do sistema para suportar:

- cadastro de usuarios, salas, disciplinas e alunos;
- alocacao de turmas (grade horaria);
- matricula de alunos em turmas;
- controle de presenca por data.

## 2. Entidades e Atributos

### 2.1 `user`
- `id` (PK)
- `username` (UNIQUE, NOT NULL)
- `email` (UNIQUE, NOT NULL)
- `password_hash` (NOT NULL)
- `role` (`admin` ou `professor`)
- `must_change_password` (NOT NULL, default `false`)
- `password_changed_at`

### 2.2 `sala`
- `id` (PK)
- `nome` (NOT NULL)
- `capacidade` (NOT NULL)

### 2.3 `disciplina`
- `id` (PK)
- `nome` (NOT NULL)
- `codigo` (UNIQUE, NOT NULL)

### 2.4 `timetable`
- `id` (PK)
- `dia` (NOT NULL)
- `hora_inicio` (NOT NULL)
- `hora_fim` (NOT NULL)
- `sala_id` (FK -> `sala.id`, NOT NULL)
- `professor_id` (FK -> `user.id`, NOT NULL)
- `disciplina_id` (FK -> `disciplina.id`, NOT NULL)

### 2.5 `aluno`
- `id` (PK)
- `nome` (NOT NULL)
- `matricula` (UNIQUE, NOT NULL)
- `created_at` (NOT NULL)

### 2.6 `matricula`
- `id` (PK)
- `aluno_id` (FK -> `aluno.id`, NOT NULL)
- `timetable_id` (FK -> `timetable.id`, NOT NULL)
- `created_at` (NOT NULL)
- `UNIQUE (aluno_id, timetable_id)`

### 2.7 `presenca`
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

## 4. Regras de Integridade

1. **Unicidade de identidade:** `user.username`, `user.email`, `aluno.matricula` e `disciplina.codigo` sao unicos.
2. **Consistencia de alocacao:**
   - `UNIQUE (dia, hora_inicio, hora_fim, sala_id)`
   - `UNIQUE (dia, hora_inicio, hora_fim, professor_id)`
3. **Consistencia de matricula:** aluno nao pode ser matriculado duas vezes na mesma turma.
4. **Consistencia de presenca:** aluno tem no maximo um registro por data na mesma turma.

## 5. Regras de Negocio Aplicadas no Backend

- Bloqueio de sobreposicao de horarios (sala/professor/aluno), incluindo conflitos parciais.
- Bloqueio de matricula quando capacidade da sala e atingida.
- Bloqueio de chamada em data futura.
- Bloqueio de chamada em dia de semana diferente do dia da turma.

## 6. Diagrama Relacional (visao textual)

`user (id)` <- `timetable.professor_id` -> `timetable (id)` <- `timetable.sala_id` -> `sala (id)`

`disciplina (id)` <- `timetable.disciplina_id`

`aluno (id)` <- `matricula.aluno_id` -> `matricula.timetable_id` -> `timetable (id)`

`aluno (id)` <- `presenca.aluno_id` -> `presenca.timetable_id` -> `timetable (id)`

## 7. Conclusao da Modelagem

A modelagem atende os criterios obrigatorios do trabalho final:

- banco relacional com entidades relacionadas;
- suporte a CRUD completo;
- regras de integridade no banco e na camada de aplicacao;
- base adequada para os fluxos administrativos e docentes.
