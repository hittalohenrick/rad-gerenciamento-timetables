# Sistema de Gerenciamento de Timetables

Sistema web para gerenciamento de timetables escolares usando Flask.

## Funcionalidades

- Login exclusivo do admin (somente o usuario admin pode autenticar)
- CRUD de salas, horarios, professores e disciplinas
- Alocacao de professores e disciplinas em horarios e salas
- Regras de validacao para evitar conflito de horario
- Exclusoes protegidas via `POST` com CSRF (sem delecao por link `GET`)

## Controle de Acesso

- O sistema e **admin-only** para autenticacao.
- Usuarios com papel `professor` existem apenas como dados de dominio para alocacao.
- Qualquer tentativa de login por perfil nao-admin e bloqueada.

## Instalacao

1. Instalar dependencias:

   ```bash
   pip install -r requirements.txt
   ```

2. Configurar banco de dados:
   - Desenvolvimento: SQLite local automatico
   - Producao: configurar `DATABASE_URL` no `.env`
   - URLs `postgres://` sao normalizadas automaticamente para `postgresql://`

3. Inicializar banco:

   ```bash
   export FLASK_APP=run.py
   flask db upgrade
   ```

4. Criar admin:

   ```bash
   python create_admin.py
   ```

5. Executar:

   ```bash
   python run.py
   ```

Acesse `http://localhost:5000`

Login padrao:
- usuario: `admin`
- senha: `admin123`

## Testes

```bash
pytest
```

## Estrutura do Projeto

- `app/`: codigo da aplicacao
- `templates/`: templates HTML
- `static/`: arquivos estaticos
- `migrations/`: migracoes
- `tests/`: testes unitarios
