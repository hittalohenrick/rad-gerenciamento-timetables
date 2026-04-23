# Documento de Design do Usuário (Fase 2 RAD)

Projeto: Sistema de Gerenciamento de Timetables

Versão: final (23/04/2026)

## 1. Objetivo

Registrar as decisões de UX/UI e navegação do sistema para os perfis `admin` e `professor`.

## 2. Fluxos de navegação

## 2.1 Fluxo administrador

1. login (`/login`)
2. dashboard (`/admin`)
3. módulos de gestão:

- salas (`/salas`)
- disciplinas (`/disciplinas`)
- professores (`/professores`)
- alunos (`/alunos`)
- horários/turmas (`/horarios`, `/timetable/*`)
- matrículas (`/matriculas`, `/matricula/*`)

## 2.2 Fluxo professor

1. login (`/login`)
2. dashboard professor (`/professor`)
3. chamada (`/professor/turma/<id>/chamada`)

## 3. Telas implementadas

- login
- dashboard admin
- dashboard professor
- CRUDs administrativos
- alocação de turmas
- alocação de alunos
- chamada com histórico

## 4. Padrões de interface adotados

1. layout base único (`base.html`) com menu por perfil;
2. feedback por `flash` em todas as operações;
3. formulários com validação visual inline;
4. tabela com ações claras (`Editar`, `Deletar`, `Resetar senha`);
5. data da chamada em formato `DD/MM/AAAA`.

## 5. Ajustes finais de UX

- remoção de excesso visual em cards;
- melhoria de legibilidade em hover de tabelas;
- campo de hora com interação 24h e teclado;
- pesquisa em seletores extensos;
- professor autenticando por `username`.

## 6. Resultado

A interface final está consistente com o escopo acadêmico: clara, objetiva, com baixo custo de explicação em apresentação e cobertura por testes E2E.
