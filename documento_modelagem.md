# Modelagem do Banco de Dados

## Projeto
Sistema de Gerenciamento de Timetables

## Objetivo da Modelagem
Organizar as informacoes academicas para controlar:
- salas
- professores
- disciplinas
- alocacoes de horario

## Tabelas Principais

### 1) `user`
- `id` (PK)
- `username` (unico)
- `email` (unico)
- `password_hash`
- `role`

Uso no sistema: usuarios administrativos e professores cadastrados para alocacao.

### 2) `sala`
- `id` (PK)
- `nome`
- `capacidade`

Uso no sistema: representa os ambientes fisicos das aulas.

### 3) `disciplina`
- `id` (PK)
- `nome`
- `codigo` (unico)

Uso no sistema: representa as materias ofertadas.

### 4) `timetable`
- `id` (PK)
- `dia`
- `hora_inicio`
- `hora_fim`
- `sala_id` (FK -> `sala.id`)
- `professor_id` (FK -> `user.id`)
- `disciplina_id` (FK -> `disciplina.id`)

Uso no sistema: registra cada alocacao de aula.

## Relacionamentos
- `sala (1) -> (N) timetable`
- `user/professor (1) -> (N) timetable`
- `disciplina (1) -> (N) timetable`

## Regras de Integridade
1. Chaves estrangeiras garantem relacao entre alocacao, sala, professor e disciplina.
2. Restricao de unicidade para evitar duplicidade exata de faixa de horario por sala.
3. Restricao de unicidade para evitar duplicidade exata de faixa de horario por professor.
4. Validacao no backend para bloquear sobreposicao de horarios (conflito parcial ou total).

## Resumo
A modelagem atende o objetivo do sistema, com entidades separadas, relacionamentos claros e regras para manter consistencia dos dados e evitar conflitos de agenda.
