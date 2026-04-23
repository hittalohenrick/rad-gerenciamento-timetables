# Estrutura do Projeto (Resumo para Apresentação)

Atualizado em: 23/04/2026

```text
rad-gerenciamento-timetables/
├── app/            # Backend Flask (modelos, formulários, rotas)
├── templates/      # Telas HTML/Jinja
├── static/         # CSS e JS
├── migrations/     # Histórico de schema do banco
├── tests/          # Unitários + E2E
├── scripts/        # Seeds de dados
├── docs/           # Documentação e evidências finais
├── run.py          # Inicialização local
├── config.py       # Configurações globais
├── requirements.txt
└── playwright.config.js
```

## Como os blocos se conectam

1. `app/routes/*` recebe requisição.
2. `app/forms.py` valida entrada.
3. `app/models.py` persiste/consulta dados.
4. `templates/*` renderiza resposta.
5. `static/*` fornece comportamento visual/interativo.
6. `tests/*` garante que tudo continua funcional.
