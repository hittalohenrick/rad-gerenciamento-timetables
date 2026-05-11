from __future__ import annotations

import argparse
import random
from datetime import time

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app import create_app, db
from app.models import Aluno, Disciplina, Matricula, Sala, Timetable, User

DAYS = ["Segunda", "Terca", "Quarta", "Quinta", "Sexta", "Sabado"]
TIME_SLOTS = [
    (time(7, 30), time(9, 10)),
    (time(9, 20), time(11, 0)),
    (time(13, 0), time(14, 40)),
    (time(14, 50), time(16, 30)),
    (time(18, 30), time(20, 10)),
    (time(20, 20), time(22, 0)),
]
MOCK_DISCIPLINAS = [
    "Algoritmos Avancados",
    "Banco de Dados II",
    "Engenharia de Software",
    "Sistemas Distribuidos",
    "Arquitetura de Computadores",
    "Interacao Humano Computador",
    "Compiladores",
    "Machine Learning",
    "Redes de Computadores II",
    "Seguranca da Informacao",
    "Computacao em Nuvem",
    "Programacao Mobile",
    "Programacao Web II",
    "Gestao de Projetos",
    "Analise de Dados",
    "Pesquisa Operacional",
    "Sistemas Embarcados",
    "Topicos em IA",
]
MOCK_SALAS = [
    ("Bloco A - Sala 101", 35),
    ("Bloco A - Sala 102", 35),
    ("Bloco A - Sala 103", 40),
    ("Bloco B - Sala 201", 45),
    ("Bloco B - Sala 202", 45),
    ("Bloco B - Sala 203", 50),
    ("Laboratorio 01", 30),
    ("Laboratorio 02", 30),
    ("Laboratorio 03", 25),
    ("Auditorio Menor", 80),
    ("Sala Multiuso", 55),
    ("Espaco Inovacao", 28),
]


def normalize(value: str) -> str:
    return (value or "").strip().lower()


def times_overlap(start1, end1, start2, end2):
    return max(start1, start2) < min(end1, end2)


def pick_unique_matriculas(existing: set[str], how_many: int):
    generated = []
    sequence = 1
    while len(generated) < how_many:
        candidate = f"MCK26-{sequence:05d}"
        sequence += 1
        if candidate in existing:
            continue
        existing.add(candidate)
        generated.append(candidate)
    return generated


def ensure_admin():
    admin = User.query.filter_by(role="admin").first()
    if admin:
        return admin
    admin = User(username="admin", email="admin@example.com", role="admin")
    admin.set_password("Admin1234")
    db.session.add(admin)
    db.session.flush()
    return admin


def ensure_mock_professores(target_total: int):
    existing = {
        normalize(user.username): user
        for user in User.query.filter(User.role == "professor").all()
    }
    created = 0

    for idx in range(1, target_total + 1):
        username = f"mock_prof_{idx:02d}"
        if normalize(username) in existing:
            continue

        professor = User(username=username, email=f"{username}@login.local", role="professor")
        professor.set_password("123456")
        db.session.add(professor)
        existing[normalize(username)] = professor
        created += 1

    return created


def ensure_mock_salas(target_total: int):
    existing = {
        normalize(sala.nome): sala
        for sala in Sala.query.all()
    }
    created = 0
    for nome, capacidade in MOCK_SALAS[:target_total]:
        if normalize(nome) in existing:
            continue
        db.session.add(Sala(nome=nome, capacidade=capacidade))
        created += 1
    return created


def ensure_mock_disciplinas(target_total: int):
    existing_names = {
        normalize(disc.nome): disc
        for disc in Disciplina.query.all()
    }
    existing_codes = {disc.codigo for disc in Disciplina.query.with_entities(Disciplina.codigo).all()}

    def next_code(start_at: int):
        sequence = start_at
        while True:
            code = f"MK{sequence:04d}"
            sequence += 1
            if code in existing_codes:
                continue
            existing_codes.add(code)
            return code, sequence

    sequence = 1
    created = 0
    for nome in MOCK_DISCIPLINAS[:target_total]:
        key = normalize(nome)
        if key in existing_names:
            continue
        code, sequence = next_code(sequence)
        db.session.add(Disciplina(nome=nome, codigo=code))
        created += 1

    return created


def build_schedule_index(timetables):
    room_index = {}
    professor_index = {}
    for turma in timetables:
        room_key = (turma.dia, turma.sala_id)
        prof_key = (turma.dia, turma.professor_id)
        room_index.setdefault(room_key, []).append((turma.hora_inicio, turma.hora_fim))
        professor_index.setdefault(prof_key, []).append((turma.hora_inicio, turma.hora_fim))
    return room_index, professor_index


def add_mock_turmas(rng: random.Random, target_new: int):
    professores = User.query.filter_by(role="professor").all()
    salas = Sala.query.all()
    disciplinas = Disciplina.query.all()

    if not professores or not salas or not disciplinas:
        return 0

    existing_turmas = Timetable.query.all()
    room_index, professor_index = build_schedule_index(existing_turmas)

    created = 0
    attempts = 0
    max_attempts = target_new * 120

    while created < target_new and attempts < max_attempts:
        attempts += 1
        dia = rng.choice(DAYS)
        hora_inicio, hora_fim = rng.choice(TIME_SLOTS)
        sala = rng.choice(salas)
        professor = rng.choice(professores)
        disciplina = rng.choice(disciplinas)

        room_busy = room_index.get((dia, sala.id), [])
        prof_busy = professor_index.get((dia, professor.id), [])

        if any(times_overlap(hora_inicio, hora_fim, start, end) for start, end in room_busy):
            continue
        if any(times_overlap(hora_inicio, hora_fim, start, end) for start, end in prof_busy):
            continue

        turma = Timetable(
            dia=dia,
            hora_inicio=hora_inicio,
            hora_fim=hora_fim,
            sala_id=sala.id,
            professor_id=professor.id,
            disciplina_id=disciplina.id,
        )
        db.session.add(turma)

        room_index.setdefault((dia, sala.id), []).append((hora_inicio, hora_fim))
        professor_index.setdefault((dia, professor.id), []).append((hora_inicio, hora_fim))
        created += 1

    return created


def add_mock_alunos(target_new: int):
    existing_matriculas = {
        matricula
        for (matricula,) in db.session.query(Aluno.matricula).all()
    }
    matriculas = pick_unique_matriculas(existing_matriculas, target_new)

    for idx, matricula in enumerate(matriculas, start=1):
        db.session.add(Aluno(nome=f"Aluno Mock {idx:03d}", matricula=matricula))

    return target_new


def build_student_schedule_index():
    student_schedule = {}
    enrollments = (
        Matricula.query.join(Timetable, Matricula.timetable_id == Timetable.id)
        .with_entities(
            Matricula.aluno_id,
            Timetable.dia,
            Timetable.hora_inicio,
            Timetable.hora_fim,
        )
        .all()
    )

    for aluno_id, dia, hora_inicio, hora_fim in enrollments:
        student_schedule.setdefault(aluno_id, {}).setdefault(dia, []).append((hora_inicio, hora_fim))

    return student_schedule


def add_mock_matriculas(rng: random.Random):
    turmas = Timetable.query.options(joinedload(Timetable.sala)).all()
    alunos = Aluno.query.all()

    if not turmas or not alunos:
        return 0

    existing_pairs = {
        (aluno_id, timetable_id)
        for aluno_id, timetable_id in db.session.query(Matricula.aluno_id, Matricula.timetable_id).all()
    }
    student_schedule = build_student_schedule_index()

    created = 0
    occupancy_profiles = [0.15, 0.3, 0.5, 0.7, 0.9, 1.0]

    for turma in turmas:
        if not turma.sala:
            continue

        capacity = max(turma.sala.capacidade, 1)
        target = int(round(capacity * rng.choice(occupancy_profiles)))
        if target <= 0:
            continue

        current_count = sum(1 for pair in existing_pairs if pair[1] == turma.id)
        remaining = max(target - current_count, 0)
        if remaining == 0:
            continue

        candidates = alunos[:]
        rng.shuffle(candidates)
        selected = 0

        for aluno in candidates:
            if selected >= remaining:
                break

            pair = (aluno.id, turma.id)
            if pair in existing_pairs:
                continue

            agenda = student_schedule.setdefault(aluno.id, {})
            day_entries = agenda.setdefault(turma.dia, [])
            if any(times_overlap(turma.hora_inicio, turma.hora_fim, start, end) for start, end in day_entries):
                continue

            db.session.add(Matricula(aluno_id=aluno.id, timetable_id=turma.id))
            day_entries.append((turma.hora_inicio, turma.hora_fim))
            existing_pairs.add(pair)
            created += 1
            selected += 1

    return created


def count_all():
    return {
        "users": db.session.query(func.count(User.id)).scalar() or 0,
        "salas": db.session.query(func.count(Sala.id)).scalar() or 0,
        "disciplinas": db.session.query(func.count(Disciplina.id)).scalar() or 0,
        "timetables": db.session.query(func.count(Timetable.id)).scalar() or 0,
        "alunos": db.session.query(func.count(Aluno.id)).scalar() or 0,
        "matriculas": db.session.query(func.count(Matricula.id)).scalar() or 0,
    }


def seed_mock_data(seed: int, target_professores: int, target_salas: int, target_disciplinas: int, new_turmas: int, new_alunos: int):
    rng = random.Random(seed)

    before = count_all()

    ensure_admin()
    created_professores = ensure_mock_professores(target_professores)
    created_salas = ensure_mock_salas(target_salas)
    created_disciplinas = ensure_mock_disciplinas(target_disciplinas)
    db.session.commit()

    created_turmas = add_mock_turmas(rng, new_turmas)
    db.session.commit()

    created_alunos = add_mock_alunos(new_alunos)
    db.session.commit()

    created_matriculas = add_mock_matriculas(rng)
    db.session.commit()

    after = count_all()

    print("=== Mock Data Seed ===")
    print(f"Seed: {seed}")
    print(f"Professores criados: {created_professores}")
    print(f"Salas criadas: {created_salas}")
    print(f"Disciplinas criadas: {created_disciplinas}")
    print(f"Turmas criadas: {created_turmas}")
    print(f"Alunos criados: {created_alunos}")
    print(f"Matriculas criadas: {created_matriculas}")
    print("--- Totais ---")
    for key in ["users", "salas", "disciplinas", "timetables", "alunos", "matriculas"]:
        print(f"{key}: {before[key]} -> {after[key]}")


def parse_args():
    parser = argparse.ArgumentParser(description="Popula o banco com dados mockados para demonstracao.")
    parser.add_argument("--seed", type=int, default=20260511)
    parser.add_argument("--target-professores", type=int, default=16)
    parser.add_argument("--target-salas", type=int, default=12)
    parser.add_argument("--target-disciplinas", type=int, default=18)
    parser.add_argument("--new-turmas", type=int, default=45)
    parser.add_argument("--new-alunos", type=int, default=120)
    return parser.parse_args()


def main():
    args = parse_args()
    app = create_app()
    with app.app_context():
        db.create_all()
        seed_mock_data(
            seed=args.seed,
            target_professores=args.target_professores,
            target_salas=args.target_salas,
            target_disciplinas=args.target_disciplinas,
            new_turmas=args.new_turmas,
            new_alunos=args.new_alunos,
        )


if __name__ == "__main__":
    main()
