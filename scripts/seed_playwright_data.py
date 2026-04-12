#!/usr/bin/env python3
"""Base deterministica para os testes E2E com Playwright."""

from __future__ import annotations

import os
import sys
from datetime import date, time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db
from app.models import Aluno, Disciplina, Matricula, Presenca, Sala, Timetable, User


def create_user(username: str, email: str, password: str, role: str, must_change_password: bool = False) -> User:
    user = User(
        username=username,
        email=email,
        role=role,
        must_change_password=must_change_password,
    )
    user.set_password(password)
    db.session.add(user)
    return user


def main() -> None:
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()

        admin = create_user('admin', 'admin@faculdade.local', 'Admin1234', 'admin')
        professor_demo = create_user('prof.demo', 'prof.demo@dcc.universidade.br', 'ProfDemo123', 'professor')

        sala_demo = Sala(nome='Laboratorio de Programacao E2E', capacidade=40)
        disciplina_demo = Disciplina(nome='Algoritmos e Programacao E2E', codigo='E2E101')

        db.session.add_all([sala_demo, disciplina_demo])
        db.session.flush()

        turma_demo = Timetable(
            dia='Quarta',
            hora_inicio=time(14, 0),
            hora_fim=time(15, 40),
            sala_id=sala_demo.id,
            professor_id=professor_demo.id,
            disciplina_id=disciplina_demo.id,
        )
        db.session.add(turma_demo)
        db.session.flush()

        alunos = [
            Aluno(nome='Aluno E2E Um', matricula='20251BCC90001'),
            Aluno(nome='Aluno E2E Dois', matricula='20251BCC90002'),
            Aluno(nome='Aluno E2E Tres', matricula='20251BCC90003'),
        ]
        db.session.add_all(alunos)
        db.session.flush()

        for aluno in alunos:
            db.session.add(Matricula(aluno_id=aluno.id, timetable_id=turma_demo.id))

        # Historico inicial para validar tabela de chamadas.
        db.session.add(
            Presenca(
                data=date(2026, 4, 1),
                presente=True,
                aluno_id=alunos[0].id,
                timetable_id=turma_demo.id,
            )
        )
        db.session.add(
            Presenca(
                data=date(2026, 4, 1),
                presente=False,
                aluno_id=alunos[1].id,
                timetable_id=turma_demo.id,
            )
        )
        db.session.add(
            Presenca(
                data=date(2026, 4, 1),
                presente=True,
                aluno_id=alunos[2].id,
                timetable_id=turma_demo.id,
            )
        )

        db.session.commit()

        print('Playwright seed concluido:')
        print(f'- admin: {admin.username} / Admin1234')
        print(f'- professor: {professor_demo.username} / ProfDemo123')
        print(f'- turma demo id: {turma_demo.id}')


if __name__ == '__main__':
    main()
