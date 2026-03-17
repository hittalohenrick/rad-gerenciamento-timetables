# Sistema de Gerenciamento de Timetables

Sistema web para gerenciamento de timetables escolares usando Flask.

## Funcionalidades

- Autenticação de usuários (admin/coordenador e professores)
- CRUD para salas, horários, professores e disciplinas (apenas admin)
- Alocação de professores/disciplinas a horários/salas
- Professores veem apenas suas alocações

## Instalação

1. Instalar dependências:

   ```bash
   pip install -r requirements.txt
   ```

2. Configurar banco de dados:
   - Para desenvolvimento: usa SQLite automaticamente
   - Para produção: configurar DATABASE_URL no .env (Supabase PostgreSQL)

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

Acesse http://localhost:5000

Login admin: admin / admin123

## Testes

Executar testes:

```bash
pytest
```

## Estrutura do Projeto

- `app/`: Código da aplicação
- `templates/`: Templates HTML
- `static/`: Arquivos estáticos
- `migrations/`: Migrations do banco
- `tests/`: Testes unitários
