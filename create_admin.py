from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    admin = User.query.filter_by(role='admin').first()
    if admin:
        print(f'Admin ja existe: {admin.username}')
    else:
        admin = User(username='admin', email='admin@example.com', role='admin', must_change_password=False)
        admin.set_password('Admin1234')
        db.session.add(admin)
        db.session.commit()
        print('Admin criado: admin / Admin1234')
