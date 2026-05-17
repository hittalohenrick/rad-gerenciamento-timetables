from __future__ import annotations

import argparse
import random
from collections import defaultdict
from datetime import time

from sqlalchemy import func

from app import create_app, db
from app.models import (
    Aluno,
    Curso,
    Disciplina,
    GradeCurricular,
    GradeCurricularItem,
    Matricula,
    Sala,
    Timetable,
    Turma,
    User,
)
from seed_curricula_base import CURRICULA, load_curricula

DAYS = ["Segunda", "Terca", "Quarta", "Quinta", "Sexta"]
TIME_SLOTS = [
    (time(7, 0), time(8, 30)),
    (time(9, 0), time(10, 30)),
    (time(13, 0), time(14, 30)),
    (time(15, 0), time(16, 30)),
    (time(18, 0), time(19, 30)),
    (time(20, 0), time(21, 30)),
]
TIME_SLOTS_BY_TURNO = {
    "matutino": [(time(7, 0), time(8, 30)), (time(9, 0), time(10, 30))],
    "vespertino": [(time(13, 0), time(14, 30)), (time(15, 0), time(16, 30))],
    "noturno": [(time(18, 0), time(19, 30)), (time(20, 0), time(21, 30))],
}
TURNO_VALUES = list(TIME_SLOTS_BY_TURNO.keys())
SEMESTER_DEFAULT = "2026.1"
MOCK_DISCIPLINAS = [
    "Algoritmos",
    "Banco de Dados",
    "Engenharia de Software",
    "Sistemas Distribuidos",
    "Arquitetura de Computadores",
    "Interacao Humano Computador",
    "Compiladores",
    "Machine Learning",
    "Redes de Computadores",
    "Seguranca da Informacao",
    "Computacao em Nuvem",
    "Programacao Mobile",
    "Programacao Web",
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
    ("Sala C - 301", 30),
    ("Sala C - 302", 30),
    ("Sala C - 303", 25),
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
    existing = {normalize(user.username): user for user in User.query.filter(User.role == "professor").all()}
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
    existing = {normalize(sala.nome): sala for sala in Sala.query.all()}
    created = 0

    for nome, capacidade in MOCK_SALAS[:target_total]:
        if normalize(nome) in existing:
            continue
        db.session.add(Sala(nome=nome, capacidade=capacidade))
        created += 1

    return created


def ensure_mock_disciplinas(target_total: int):
    # Mantido por compatibilidade de assinatura; a carga curricular base ja cria o catalogo necessario.
    return 0


def ensure_professor_aptidoes(rng: random.Random):
    professores = User.query.filter_by(role="professor").all()
    disciplinas_curriculares = (
        db.session.query(Disciplina)
        .join(GradeCurricularItem, GradeCurricularItem.disciplina_id == Disciplina.id)
        .join(GradeCurricular, GradeCurricularItem.grade_id == GradeCurricular.id)
        .filter(GradeCurricular.ativa.is_(True))
        .distinct()
        .all()
    )
    if not professores or not disciplinas_curriculares:
        return 0

    updated = 0
    for professor in professores:
        min_size = min(8, len(disciplinas_curriculares))
        max_size = min(20, len(disciplinas_curriculares))
        if max_size == 0:
            continue
        if len(professor.disciplinas_aptas) >= min_size:
            continue

        sample_size = rng.randint(min_size, max_size)
        professor.disciplinas_aptas = rng.sample(disciplinas_curriculares, sample_size)
        updated += 1

    return updated


def add_mock_turmas(rng: random.Random, target_new: int):
    cursos = Curso.query.order_by(Curso.id.asc()).all()
    if not cursos:
        return 0

    existing = {
        (curso_id, normalize(codigo), normalize(semestre_letivo))
        for curso_id, codigo, semestre_letivo in db.session.query(
            Turma.curso_id,
            Turma.codigo,
            Turma.semestre_letivo,
        ).all()
    }

    created = 0
    attempts = 0
    max_attempts = target_new * 60
    sequence = 1

    while created < target_new and attempts < max_attempts:
        attempts += 1
        curso = rng.choice(cursos)
        grade_ativa = (
            GradeCurricular.query.filter_by(curso_id=curso.id, ativa=True)
            .order_by(GradeCurricular.id.desc())
            .first()
        )
        if grade_ativa is None:
            continue
        periodos_validos = {
            periodo
            for (periodo,) in db.session.query(GradeCurricularItem.periodo)
            .filter(GradeCurricularItem.grade_id == grade_ativa.id)
            .all()
            if 1 <= periodo <= (curso.quantidade_periodos or 1)
        }
        if not periodos_validos:
            continue
        periodo = rng.choice(sorted(periodos_validos))
        codigo = f"{curso.codigo}-P{periodo}-{sequence:02d}"
        sequence += 1
        key = (curso.id, normalize(codigo), normalize(SEMESTER_DEFAULT))
        if key in existing:
            continue

        turma = Turma(
            curso_id=curso.id,
            codigo=codigo,
            semestre_letivo=SEMESTER_DEFAULT,
            periodo=periodo,
            turno=rng.choice(TURNO_VALUES),
            quantidade_alunos=rng.choice([25, 30, 35, 40]),
            ativa=True,
        )
        db.session.add(turma)
        existing.add(key)
        created += 1

    return created


def _grade_disciplinas_por_turma():
    rows = (
        db.session.query(Turma.id, GradeCurricularItem.disciplina_id)
        .join(GradeCurricular, GradeCurricular.curso_id == Turma.curso_id)
        .join(GradeCurricularItem, GradeCurricularItem.grade_id == GradeCurricular.id)
        .filter(
            GradeCurricular.ativa.is_(True),
            GradeCurricularItem.periodo == Turma.periodo,
        )
        .all()
    )

    by_turma = defaultdict(list)
    for turma_id, disciplina_id in rows:
        by_turma[turma_id].append(disciplina_id)

    return by_turma


def _build_schedule_index(timetables):
    room_index = defaultdict(list)
    professor_index = defaultdict(list)
    turma_index = defaultdict(list)

    for row in timetables:
        room_index[(row.dia, row.sala_id)].append((row.hora_inicio, row.hora_fim))
        professor_index[(row.dia, row.professor_id)].append((row.hora_inicio, row.hora_fim))
        turma_index[(row.dia, row.turma_id)].append((row.hora_inicio, row.hora_fim))

    return room_index, professor_index, turma_index


def add_mock_timetables(rng: random.Random, target_new: int):
    salas = Sala.query.all()
    professores = User.query.filter_by(role="professor").all()
    turmas = Turma.query.all()
    if not salas or not professores or not turmas:
        return 0

    professor_aptidoes = {
        professor.id: {disciplina.id for disciplina in professor.disciplinas_aptas}
        for professor in professores
    }
    disciplinas_por_turma = _grade_disciplinas_por_turma()

    existing = Timetable.query.all()
    room_index, professor_index, turma_index = _build_schedule_index(existing)

    created = 0
    attempts = 0
    max_attempts = target_new * 120

    while created < target_new and attempts < max_attempts:
        attempts += 1
        turma = rng.choice(turmas)
        allowed_disciplines = disciplinas_por_turma.get(turma.id, [])
        if not allowed_disciplines:
            continue

        disciplina_id = rng.choice(allowed_disciplines)
        eligible_professors = [
            professor
            for professor in professores
            if disciplina_id in professor_aptidoes.get(professor.id, set())
        ]
        if not eligible_professors:
            continue

        dia = rng.choice(DAYS)
        allowed_slots = TIME_SLOTS_BY_TURNO.get(turma.turno, TIME_SLOTS)
        hora_inicio, hora_fim = rng.choice(allowed_slots)
        sala = rng.choice(salas)
        professor = rng.choice(eligible_professors)

        room_busy = room_index[(dia, sala.id)]
        prof_busy = professor_index[(dia, professor.id)]
        turma_busy = turma_index[(dia, turma.id)]

        if any(times_overlap(hora_inicio, hora_fim, start, end) for start, end in room_busy):
            continue
        if any(times_overlap(hora_inicio, hora_fim, start, end) for start, end in prof_busy):
            continue
        if any(times_overlap(hora_inicio, hora_fim, start, end) for start, end in turma_busy):
            continue

        db.session.add(
            Timetable(
                dia=dia,
                hora_inicio=hora_inicio,
                hora_fim=hora_fim,
                sala_id=sala.id,
                professor_id=professor.id,
                disciplina_id=disciplina_id,
                turma_id=turma.id,
            )
        )
        room_index[(dia, sala.id)].append((hora_inicio, hora_fim))
        professor_index[(dia, professor.id)].append((hora_inicio, hora_fim))
        turma_index[(dia, turma.id)].append((hora_inicio, hora_fim))
        created += 1

    return created


def add_mock_alunos(target_new: int):
    cursos = Curso.query.order_by(Curso.nome.asc()).all()
    if not cursos:
        return 0
    existing_matriculas = {matricula for (matricula,) in db.session.query(Aluno.matricula).all()}
    matriculas = pick_unique_matriculas(existing_matriculas, target_new)

    for idx, matricula in enumerate(matriculas, start=1):
        curso = cursos[(idx - 1) % len(cursos)]
        db.session.add(Aluno(nome=f"Aluno Mock {idx:03d}", matricula=matricula, curso_id=curso.id))

    return target_new


def _build_turma_slots():
    rows = (
        db.session.query(Timetable.turma_id, Timetable.dia, Timetable.hora_inicio, Timetable.hora_fim)
        .order_by(Timetable.turma_id.asc())
        .all()
    )
    by_turma = defaultdict(list)
    for turma_id, dia, hora_inicio, hora_fim in rows:
        by_turma[turma_id].append((dia, hora_inicio, hora_fim))
    return by_turma


def add_mock_matriculas(rng: random.Random):
    turmas = Turma.query.all()
    alunos = Aluno.query.all()
    if not turmas or not alunos:
        return 0

    turma_slots = _build_turma_slots()
    existing_pairs = {
        (aluno_id, turma_id)
        for aluno_id, turma_id in db.session.query(Matricula.aluno_id, Matricula.turma_id).all()
    }

    aluno_turmas = defaultdict(set)
    for aluno_id, turma_id in existing_pairs:
        aluno_turmas[aluno_id].add(turma_id)

    created = 0
    occupancy_profiles = [0.2, 0.4, 0.6, 0.8, 1.0]

    def has_schedule_conflict(aluno_id: int, target_turma_id: int) -> bool:
        target_slots = turma_slots.get(target_turma_id, [])
        for enrolled_turma_id in aluno_turmas.get(aluno_id, set()):
            for target_day, target_start, target_end in target_slots:
                for other_day, other_start, other_end in turma_slots.get(enrolled_turma_id, []):
                    if other_day != target_day:
                        continue
                    if times_overlap(target_start, target_end, other_start, other_end):
                        return True
        return False

    for turma in turmas:
        if not turma_slots.get(turma.id):
            continue

        capacidade = max(turma.quantidade_alunos or 0, 1)
        target = int(round(capacidade * rng.choice(occupancy_profiles)))
        current = sum(1 for _, turma_id in existing_pairs if turma_id == turma.id)
        remaining = max(target - current, 0)
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
            if has_schedule_conflict(aluno.id, turma.id):
                continue

            db.session.add(Matricula(aluno_id=aluno.id, turma_id=turma.id))
            existing_pairs.add(pair)
            aluno_turmas[aluno.id].add(turma.id)
            created += 1
            selected += 1

    return created


def count_all():
    return {
        "users": db.session.query(func.count(User.id)).scalar() or 0,
        "cursos": db.session.query(func.count(Curso.id)).scalar() or 0,
        "grades": db.session.query(func.count(GradeCurricular.id)).scalar() or 0,
        "grade_items": db.session.query(func.count(GradeCurricularItem.id)).scalar() or 0,
        "turmas": db.session.query(func.count(Turma.id)).scalar() or 0,
        "salas": db.session.query(func.count(Sala.id)).scalar() or 0,
        "disciplinas": db.session.query(func.count(Disciplina.id)).scalar() or 0,
        "timetables": db.session.query(func.count(Timetable.id)).scalar() or 0,
        "alunos": db.session.query(func.count(Aluno.id)).scalar() or 0,
        "matriculas": db.session.query(func.count(Matricula.id)).scalar() or 0,
    }


def seed_mock_data(
    seed: int,
    target_professores: int,
    target_salas: int,
    target_disciplinas: int,
    new_turmas: int,
    new_timetables: int,
    new_alunos: int,
):
    rng = random.Random(seed)
    # Garante ES(10), CC(8), ADS(5) e as respectivas grades base.
    load_curricula()
    before = count_all()

    ensure_admin()
    created_professores = ensure_mock_professores(target_professores)
    created_salas = ensure_mock_salas(target_salas)
    created_disciplinas = ensure_mock_disciplinas(target_disciplinas)
    created_cursos = 0
    created_grades = 0
    created_grade_items = 0
    updated_aptidoes = ensure_professor_aptidoes(rng)
    db.session.commit()

    created_turmas = add_mock_turmas(rng, new_turmas)
    db.session.commit()

    created_timetables = add_mock_timetables(rng, new_timetables)
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
    print(f"Cursos criados: {created_cursos}")
    print(f"Grades criadas: {created_grades}")
    print(f"Itens de grade criados: {created_grade_items}")
    print(f"Professores com aptidoes atualizadas: {updated_aptidoes}")
    print(f"Turmas criadas: {created_turmas}")
    print(f"Alocacoes (timetable) criadas: {created_timetables}")
    print(f"Alunos criados: {created_alunos}")
    print(f"Matriculas criadas: {created_matriculas}")
    print("--- Totais ---")
    for key in [
        "users",
        "cursos",
        "grades",
        "grade_items",
        "turmas",
        "salas",
        "disciplinas",
        "timetables",
        "alunos",
        "matriculas",
    ]:
        print(f"{key}: {before[key]} -> {after[key]}")


def parse_args():
    parser = argparse.ArgumentParser(description="Popula o banco com dados mockados para demonstracao.")
    parser.add_argument("--seed", type=int, default=20260511)
    parser.add_argument("--target-professores", type=int, default=16)
    parser.add_argument("--target-salas", type=int, default=12)
    parser.add_argument("--target-disciplinas", type=int, default=0)
    parser.add_argument("--new-turmas", type=int, default=24)
    parser.add_argument("--new-timetables", type=int, default=120)
    parser.add_argument("--new-alunos", type=int, default=160)
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
            new_timetables=args.new_timetables,
            new_alunos=args.new_alunos,
        )


if __name__ == "__main__":
    main()
