# Estrutura do Projeto (Slide Pronto)

## 1. Arquitetura em 5 blocos

1. `app/`: backend Flask (regras, validações e persistência).
2. `templates/` + `static/`: interface web.
3. `migrations/`: evolução do banco.
4. `tests/`: qualidade (pytest + Playwright).
5. `docs/`: documentação e evidências finais.

## 2. Fluxo principal

1. usuário acessa rota (`app/routes`);
2. formulário valida (`app/forms.py`);
3. regra de negócio executa (`helpers` + rotas);
4. ORM persiste (`app/models.py`);
5. template renderiza resposta (`templates`).

## 3. Arquivos da raiz para destacar na banca

- `run.py`: sobe aplicação.
- `config.py`: configura ambiente.
- `requirements.txt`: dependências Python.
- `playwright.config.js`: configuração E2E.
- `README.md`: guia de setup/testes.

## 4. Evidência final

- Testes unitários: **21 passed**.
- Testes E2E: **5 passed**.
- Vídeo de funcionalidades: `docs/evidencias/video_teste_funcionalidades.webm`.
