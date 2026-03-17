from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    # Criar admin
    admin = User(username='admin', email='admin@example.com', role='admin')
    admin.set_password('admin123')
    db.session.add(admin)
    db.session.commit()
    print('Admin criado: admin / admin123')