# Relatório do Projeto - Sistema de Gerenciamento de Timetables

Versão: 27/04/2026

## 1. Informações Gerais

- **Nome do Projeto:** Sistema de Gerenciamento de Timetables
- **Equipe:** Paulo Henrique Lima da Silva - 202208731015; Luis Filipe da Silva França - 202303761791; Octacilio Ferreira dos Santos - 202508435251; Hittalo Henrick Souza Pinto - 202402334311
- **Data de Início:** 16/03/2026
- **Data de Conclusão:** 18/05/2026 (prevista)

## 2. Introdução

### Objetivo do Projeto

O projeto tem como objetivo desenvolver uma aplicação web para organizar grade acadêmica, alocação de turmas e controle de presença em sala de aula. A solução substitui processos manuais, reduz conflitos de horário e melhora o acompanhamento das turmas por perfis distintos de usuário (`admin` e `professor`).

## 3. Planejamento de Requisitos (Fase 1 do RAD)

### Requisitos Funcionais

- O sistema deve permitir autenticação de usuários por login e senha.
- O sistema deve permitir CRUD de salas.
- O sistema deve permitir CRUD de disciplinas.
- O sistema deve permitir CRUD de professores.
- O sistema deve permitir CRUD de alunos.
- O sistema deve permitir criação, edição e exclusão de alocações de turma/horário.
- O sistema deve permitir matrícula de alunos em turmas.
- O sistema deve permitir registro de presença por turma e data.
- O sistema deve diferenciar permissões por perfil de acesso (`admin` e `professor`).

### Requisitos Não Funcionais

- A aplicação deve ser desenvolvida em Python com framework web.
- O banco de dados deve ser relacional e com integridade referencial.
- Os formulários devem validar obrigatoriedade, formato e consistência dos dados.
- O sistema deve apresentar mensagens claras de sucesso/erro para cada operação.
- O código deve ser organizado em módulos para facilitar manutenção e evolução.

### Ferramentas Utilizadas

- Linguagem: Python 3
- Framework web: Flask
- Persistência: SQLAlchemy
- Banco de dados: SQLite
- Frontend: HTML, CSS e JavaScript
- Versionamento: Git

## 4. Design do Usuário (Fase 2 do RAD)

### Protótipos de Interface

Foram estruturados fluxos de interface para os dois perfis principais:

- Login e navegação inicial por perfil.
- Painel administrativo para CRUDs e alocações.
- Painel do professor para visualização de turmas e chamada.

Os protótipos evoluíram para as telas implementadas em `templates/`, com foco em clareza visual e redução de passos nas operações principais.

### Discussões de Design

Durante os ciclos iterativos da fase RAD, as principais discussões envolveram:

- Separação de responsabilidades entre menus de administrador e professor.
- Simplificação da entrada de horário no formato 24h.
- Melhoria da leitura de dados (listas de alunos, turmas e presenças).
- Redução de ruído visual para acelerar tarefas frequentes de cadastro e chamada.

### Decisões Tomadas

- Acesso baseado em papéis para restringir funcionalidades sensíveis.
- Organização do painel administrativo por entidades (salas, disciplinas, professores, alunos, matrículas e horários).
- Fluxo de presença concentrado na tela da turma do professor, com validação de data.
- Padronização de formulários e mensagens de feedback para todas as operações.

## 5. Construção (Fase 3 do RAD)

### Desenvolvimento

O desenvolvimento foi incremental, iniciando pela base de autenticação e estrutura do projeto, seguido por:

1. Modelagem e migrações do banco de dados.
2. Implementação de CRUDs.
3. Implementação de alocação de horários e matrícula.
4. Implementação do fluxo de chamada por professor.
5. Refinamentos de validação e usabilidade.

Desafios técnicos principais:

- Evitar conflito de horário para sala e professor na mesma faixa de tempo.
- Impedir matrícula acima da capacidade da sala.
- Validar coerência da data da chamada com o dia da turma.
- Preservar integridade ao impedir exclusões com vínculos ativos.

### Distribuição das Tarefas

A equipe trabalhou por frentes de desenvolvimento e validação, com revisão coletiva do resultado final:

- Levantamento de requisitos e consolidação do escopo.
- Modelagem de dados e migrações.
- Backend (rotas, regras de negócio e validações).
- Frontend (templates e padronização visual).
- Testes funcionais manuais e ajustes finais de documentação.

### Integração Contínua

A integração foi realizada por versionamento em Git, com commits incrementais e validação contínua das funcionalidades após cada conjunto de alterações. Não foi configurado pipeline CI automatizado; a integração foi conduzida localmente com execução da aplicação e testes de fluxo.

## 6. Transição (Fase 4 do RAD)

### Testes Realizados

Foram executados testes funcionais manuais, cobrindo os fluxos críticos:

- Autenticação e redirecionamento por perfil.
- CRUD completo de salas, disciplinas, professores e alunos.
- Criação e edição de horários com bloqueio de conflitos.
- Matrícula com validação de capacidade e choque de horário.
- Registro de presença com validação de data e atualização de registros existentes.
- Bloqueio de exclusão quando existem dependências relacionais.

Também foi criada uma suíte automatizada de testes em Python com `pytest`, cobrindo:

- login com credencial inválida e login válido de administrador;
- fluxo completo de CRUD de sala (criar, editar e excluir);
- detecção de conflito de alocação por sobreposição de sala;
- bloqueio de matrícula quando capacidade da sala é atingida;
- bloqueio de chamada em data futura;
- registro de chamada em data válida.

Resultado da execução em 27/04/2026:

- Comando: `.venv/bin/pytest -q`
- Saída: `7 passed in 27.17s`

### Feedback do Usuário

Os testes de uso com foco acadêmico indicaram necessidade de simplificação dos formulários e mensagens mais diretas. Como resposta, foram aplicados ajustes de usabilidade, principalmente no fluxo de professor e na padronização visual das telas de cadastro.

### Implantação

O sistema foi implantado em ambiente local para validação final (execução via Flask, banco SQLite no diretório `instance/`).

## 7. Conclusões

### Resultados Alcancados

O projeto atendeu ao objetivo de entregar uma aplicação RAD funcional com interface web, backend em Python, banco relacional e operações de CRUD com validações de negócio.

### Aprendizados

Os principais aprendizados da equipe envolveram:

- Aplicação prática das fases do RAD em ciclos curtos.
- Importância de validações de regra de negócio além das validações de formulário.
- Cuidado com integridade de dados em operações de exclusão e atualização.
- Ganho de produtividade com organização modular do código.

### Próximos Passos (Opcional)

- Expandir a suíte automatizada para cobrir todos os CRUDs e cenários negativos adicionais.
- Publicar a aplicação em ambiente de hospedagem.
- Adicionar relatórios gerenciais (por sala, disciplina e frequência).
- Incluir exportação de dados em formatos como CSV/PDF.

## 8. Anexos (Opcional)

### Código Fonte

- Repositório remoto: não informado no momento.

## Formato Geral

- **Fonte:** Arial ou Calibri, tamanho 12.
- **Espaçamento:** 1.5 entre linhas.
- **Alinhamento:** Justificado.
- **Citações e Referências:** utilizar padrão acadêmico (ABNT ou APA) na versão final de entrega.
