# Estrutura do Projeto

## Arquitetura em 5 blocos

1. `app/`: núcleo do sistema (modelos, rotas e regras de negócio).
2. `templates/` + `static/`: camada de interface (telas, CSS e JS).
3. `migrations/`: histórico e evolução do banco de dados.
4. `tests/`: qualidade com testes backend e ponta a ponta.
5. `scripts/`: geração de dados para demonstração e testes.

## Fluxo da aplicação

1. Usuário acessa rota (`app/routes`).
2. Dados são validados (`app/forms.py`).
3. Regras de negócio são aplicadas (`helpers` + rotas).
4. Persistência no banco (`app/models.py` + SQLAlchemy).
5. Resposta renderizada em tela (`templates/`).

## Arquivos-chave da raiz

1. `run.py`: inicializa a aplicação Flask.
2. `config.py`: centraliza as configurações.
3. `requirements.txt`: dependências Python.
4. `package.json`: dependências/scripts E2E.
5. `README.md`: guia de execução e uso.

## Mensagem para a banca (fala curta)

Arquitetura simples, separada por responsabilidades, com controle de acesso por perfil, regras de integridade no backend e testes automatizados para garantir confiabilidade.
