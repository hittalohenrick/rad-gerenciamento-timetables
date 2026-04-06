# Documento de Planejamento de Requisitos

## Sistema de Gerenciamento de TimeTables

- **Curso/Disciplina:** Desenvolvimento de Sistemas
- **Data:** 23 de marco de 2026

## 1. Introducao

Este documento descreve os requisitos funcionais e a arquitetura tecnica para o sistema de Gerenciamento de TimeTables. O objetivo do sistema e permitir que administradores gerenciem a alocacao de professores e disciplinas em salas de aula de forma organizada e eficiente.

## 2. Arquitetura e Stack Tecnologica

O projeto sera desenvolvido seguindo padroes de mercado para garantir manutenibilidade e escalabilidade inicial:

- **Linguagem:** Python 3.x
- **Framework Web:** Flask
- **Banco de Dados:** SQLite (padrao para desenvolvimento e portabilidade)
- **ORM:** SQLAlchemy (via Flask-SQLAlchemy)
- **Versionamento de Banco:** Flask-Migrate (Alembic)
- **Seguranca:** Hashing de senhas para o Admin (Werkzeug Security)

## 3. Requisitos Funcionais

### 3.1 RF01 - Autenticacao de Administrador

- **Tela de Login:** Campos para Usuario e Senha.
- **Seguranca:** Acesso restrito as areas de gerenciamento apenas para usuarios autenticados.

### 3.2 RF02 - Gerenciamento de Salas

Permite o controle fisico dos espacos de aula.

- **Atributos:** Nome da Sala, Capacidade (inteiro).
- **Acoes:** Cadastrar nova sala, editar dados existentes e excluir salas.

### 3.3 RF03 - Gerenciamento de Professores

Manutencao do corpo docente.

- **Atributos:** Nome, E-mail (unico).
- **Acoes:** Cadastrar, editar e excluir professores.

### 3.4 RF04 - Gerenciamento de Disciplinas

Catalogo de materias ofertadas.

- **Atributos:** Nome, Codigo Automatico (gerado pelo sistema/DB).
- **Acoes:** Cadastrar, editar e excluir disciplinas.

### 3.5 RF05 - Gerenciamento de Alocacoes (TimeTables)

Nucleo do sistema, onde ocorre a juncao das entidades.

- **Atributos:** Dia da semana, Horario de Inicio, Horario de Fim, Sala (FK), Professor (FK), Disciplina (FK).
- **Regras de Negocio:** O sistema deve evitar conflitos de horario para a mesma sala ou para o mesmo professor (validacao via SQLAlchemy/aplicacao).

## 4. Modelo de Dados Sugerido

Para suportar o SQLAlchemy, as tabelas seguirao a seguinte logica de relacionamento:

| Entidade | Chave Primaria | Relacionamentos |
|---|---|---|
| User (Admin) | id | - |
| Sala | id | Has Many Alocacoes |
| Professor | id | Has Many Alocacoes |
| Disciplina | id | Has Many Alocacoes |
| Alocacao | id | Belongs To (Sala, Professor, Disciplina) |

## 5. Requisitos Nao Funcionais

1. **Persistencia:** Todos os dados devem ser persistidos no SQLite.
2. **Integridade:** Uso de Foreign Keys para garantir que uma alocacao nao aponte para uma sala inexistente.
3. **Interface:** Design responsivo e intuitivo para o administrador.
