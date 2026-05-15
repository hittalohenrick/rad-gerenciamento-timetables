# Spec 002 - UX de Disciplinas Aptas do Professor

## Objetivo
Melhorar a experiencia de cadastro/edicao de professores para que a selecao de `Disciplinas Aptas` seja clara, multipla e persistente.

## Problema Atual
- A selecao multipla nao esta intuitiva.
- Ao editar, disciplinas previamente salvas podem aparentar estar em branco.
- O admin precisa conseguir evoluir aptidoes em etapas sem perder selecoes anteriores.

## User Stories
1. Como admin, quero selecionar varias disciplinas aptas sem depender de atalhos de teclado.
2. Como admin, quero abrir a edicao e visualizar imediatamente as disciplinas ja marcadas.
3. Como admin, quero adicionar novas disciplinas aptas em etapas e salvar mantendo as anteriores.

## Criterios de Aceite
1. O formulario de professor permite marcar multiplas disciplinas por clique direto (sem Ctrl/Cmd).
2. Na edicao, disciplinas previamente vinculadas aparecem marcadas.
3. Ao salvar edicao com disciplinas antigas + novas, todas permanecem vinculadas.
4. O formulario possui busca local para facilitar encontrar disciplinas.
5. Testes automatizados cobrem criacao multipla e persistencia na edicao.

## Fora de Escopo
- Alterar regras de alocacao de professores em horarios.
- Criar niveis de proficiencia por disciplina.
