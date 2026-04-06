# Protótipo da Interface

## Projeto
Sistema de Gerenciamento de Timetables

## Objetivo do Protótipo
Apresentar, de forma simples, as principais telas da interface administrativa do sistema e o fluxo de navegação utilizado pelo usuário.

## Visão Geral da Interface
- Interface web desenvolvida com Flask + templates HTML/Jinja.
- Layout responsivo com Bootstrap.
- Navegação centralizada no painel administrativo.
- Feedback visual com mensagens de sucesso, aviso e erro.

## Fluxo Principal
1. Login do administrador.
2. Acesso ao Dashboard Administrativo.
3. Navegação para as telas de gerenciamento:
- Salas
- Professores
- Disciplinas
- Horários/Alocações
4. Cadastro, edição e exclusão de registros.

## Telas do Protótipo

### 1) Tela de Login
Função:
- autenticar o administrador.

Pontos de interface:
- campo de usuário;
- campo de senha;
- botão de entrada;
- alerta para credenciais inválidas.

Espaço para print:
**[INSERIR PRINT DA TELA DE LOGIN AQUI]**

### 2) Dashboard Administrativo
Função:
- apresentar visão geral do sistema.

Pontos de interface:
- cards com indicadores (salas, professores, disciplinas e alocações);
- atalhos para cada módulo;
- listagem de alocações recentes.

Espaço para print:
**[INSERIR PRINT DO DASHBOARD AQUI]**

### 3) Tela de Salas
Função:
- manter cadastro de salas.

Pontos de interface:
- listagem de salas;
- ação de nova sala;
- ação de editar;
- ação de excluir.

Espaço para print:
**[INSERIR PRINT DA TELA DE SALAS AQUI]**

### 4) Tela de Professores
Função:
- manter cadastro de professores para alocação.

Pontos de interface:
- listagem de professores;
- ação de novo professor;
- ação de editar;
- ação de excluir.

Espaço para print:
**[INSERIR PRINT DA TELA DE PROFESSORES AQUI]**

### 5) Tela de Disciplinas
Função:
- manter cadastro de disciplinas.

Pontos de interface:
- listagem de disciplinas;
- ação de nova disciplina;
- ação de editar;
- ação de excluir.

Espaço para print:
**[INSERIR PRINT DA TELA DE DISCIPLINAS AQUI]**

### 6) Formulário de Nova Alocação
Função:
- criar alocação de horário de aula.

Pontos de interface:
- seleção de dia;
- horário de início e fim em formato tradicional `HH:MM`;
- seleção de sala, professor e disciplina;
- validação de conflito de horário.

Espaço para print:
**[INSERIR PRINT DO FORMULÁRIO DE ALOCAÇÃO AQUI]**

## Conclusão
O protótipo atende ao objetivo de oferecer uma interface simples, organizada e funcional para a gestão de timetables, com foco no uso administrativo e nas operações de CRUD.
