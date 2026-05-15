# Spec 000 - Dominio da Faculdade de TI

## Contexto
Sistema academico para operacao de uma faculdade de TI, com foco em planejamento de oferta semestral e execucao de aulas.

## Entidades Centrais
- Sala: ambiente fisico com capacidade.
- Curso: oferta academica principal (ex.: ADS, SI, CC).
- Disciplina: unidade curricular.
- Grade Curricular: conjunto de disciplinas por periodo para um curso.
- Turma: oferta semestral de um curso, com periodo e turno.
- Aluno: pessoa matriculavel.
- Matricula: vinculo aluno-turma.
- Professor: usuario docente com aptidoes por disciplina.
- Timetable (Horario): aula em dia/tempo/sala/disciplina/turma, com professor opcional ate alocacao final.

## Regras de Negocio
1. Cada turma pertence a um curso, semestre letivo, periodo e turno.
2. Toda turma depende de grade curricular ativa do curso.
3. As disciplinas permitidas para turma sao as do periodo da grade ativa.
4. O quadro da turma distribui disciplinas entre segunda e sexta em slots do turno.
5. Slots validos por turno:
- Matutino: 07:00-08:30, 09:00-10:30
- Vespertino: 13:00-14:30, 15:00-16:30
- Noturno: 18:00-19:30, 20:00-21:30
6. Um horario nao pode conflitar em sobreposicao para:
- mesma sala
- mesmo professor
- mesma turma
7. O quadro da turma deve ficar completo antes da etapa de alocacao docente.
8. Professor so pode ser alocado em disciplina para a qual possui aptidao e disponibilidade no slot.
9. Aluno nao pode ter conflito de horario entre turmas matriculadas.

## Fluxo Operacional Ideal
1. Cadastrar salas.
2. Cadastrar cursos.
3. Montar grade curricular ativa por curso.
4. Cadastrar disciplinas.
5. Abrir turmas por semestre/periodo/turno.
6. Gerar quadro da turma (disciplinas -> dia/tempo/sala).
7. Cadastrar professores e aptidoes.
8. Alocar professores nos horarios gerados.
9. Cadastrar alunos.
10. Matricular alunos em turmas.
11. Professores realizam chamada por aula.

## Criterios de Aceite Macro
1. Admin consegue identificar pendencias do fluxo em um unico painel.
2. Geracao de quadro funciona sem professor inicial.
3. Alocacao docente posterior respeita aptidao e conflitos.
4. Professor visualiza agenda semanal com acesso rapido para chamada.
