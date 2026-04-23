#!/usr/bin/env python3
"""Gera dados mockados para um cenario realista de Ciencia da Computacao."""

from __future__ import annotations

import argparse
import os
import random
import re
import sys
from collections import defaultdict
from datetime import date, time, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db
from app.models import Aluno, Disciplina, Matricula, Presenca, Sala, Timetable, User

DAYS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"]
DAY_TO_WEEKDAY = {
    "Segunda": 0,
    "Terca": 1,
    "Terça": 1,
    "Quarta": 2,
    "Quinta": 3,
    "Sexta": 4,
    "Sabado": 5,
    "Sábado": 5,
    "Domingo": 6,
}

SLOTS = [
    (time(7, 0), time(8, 40)),
    (time(8, 50), time(10, 30)),
    (time(10, 40), time(12, 20)),
    (time(13, 30), time(15, 10)),
    (time(15, 20), time(17, 0)),
    (time(17, 10), time(18, 50)),
    (time(19, 0), time(20, 40)),
    (time(20, 50), time(22, 30)),
]

FIRST_NAMES = [
    "Ana",
    "Andre",
    "Bianca",
    "Bruno",
    "Camila",
    "Carlos",
    "Carolina",
    "Cesar",
    "Daniel",
    "Debora",
    "Diego",
    "Eduarda",
    "Eliane",
    "Fabio",
    "Felipe",
    "Fernanda",
    "Gabriel",
    "Gabriela",
    "Guilherme",
    "Helena",
    "Igor",
    "Isabela",
    "Joana",
    "Joao",
    "Julia",
    "Karina",
    "Larissa",
    "Leonardo",
    "Leticia",
    "Lucas",
    "Luiza",
    "Marcelo",
    "Mariana",
    "Mateus",
    "Natasha",
    "Nicolas",
    "Paulo",
    "Rafael",
    "Raissa",
    "Renata",
    "Ricardo",
    "Rodrigo",
    "Sabrina",
    "Samuel",
    "Talita",
    "Tatiane",
    "Thiago",
    "Vanessa",
    "Vitoria",
    "Yasmin",
]

LAST_NAMES = [
    "Albuquerque",
    "Almeida",
    "Araujo",
    "Barbosa",
    "Batista",
    "Braga",
    "Carvalho",
    "Costa",
    "Cruz",
    "Dantas",
    "Dias",
    "Fernandes",
    "Ferreira",
    "Figueiredo",
    "Freitas",
    "Gomes",
    "Lima",
    "Lopes",
    "Machado",
    "Martins",
    "Melo",
    "Mendes",
    "Moraes",
    "Moreira",
    "Nascimento",
    "Nogueira",
    "Oliveira",
    "Pereira",
    "Queiroz",
    "Ramos",
    "Rezende",
    "Ribeiro",
    "Rocha",
    "Sales",
    "Santana",
    "Santos",
    "Silva",
    "Soares",
    "Souza",
    "Teixeira",
    "Vieira",
]

DISCIPLINE_CATALOG = [
    ("Introducao a Ciencia da Computacao", "CCO101"),
    ("Algoritmos e Programacao", "CCO102"),
    ("Laboratorio de Programacao I", "CCO103"),
    ("Matematica Discreta", "MAT110"),
    ("Calculo Diferencial e Integral I", "MAT101"),
    ("Calculo Diferencial e Integral II", "MAT102"),
    ("Algebra Linear", "MAT120"),
    ("Probabilidade e Estatistica", "MAT210"),
    ("Estruturas de Dados", "CCO201"),
    ("Programacao Orientada a Objetos", "CCO202"),
    ("Laboratorio de Programacao II", "CCO203"),
    ("Arquitetura e Organizacao de Computadores", "CCO210"),
    ("Sistemas Digitais", "CCO211"),
    ("Programacao Funcional", "CCO212"),
    ("Banco de Dados I", "CCO220"),
    ("Banco de Dados II", "CCO320"),
    ("Sistemas Operacionais I", "CCO230"),
    ("Sistemas Operacionais II", "CCO330"),
    ("Redes de Computadores I", "CCO240"),
    ("Redes de Computadores II", "CCO340"),
    ("Engenharia de Software I", "CCO250"),
    ("Engenharia de Software II", "CCO350"),
    ("Engenharia de Requisitos", "CCO251"),
    ("Testes de Software", "CCO352"),
    ("Qualidade de Software", "CCO353"),
    ("Analise e Projeto de Sistemas", "CCO351"),
    ("Linguagens Formais e Automatos", "CCO260"),
    ("Teoria da Computacao", "CCO261"),
    ("Compiladores", "CCO360"),
    ("Paradigmas de Programacao", "CCO270"),
    ("Analise de Algoritmos", "CCO271"),
    ("Computacao Concorrente e Paralela", "CCO272"),
    ("Inteligencia Artificial", "CCO370"),
    ("Aprendizado de Maquina", "CCO470"),
    ("Mineracao de Dados", "CCO471"),
    ("Ciencia de Dados", "CCO472"),
    ("Processamento de Linguagem Natural", "CCO473"),
    ("Computacao Grafica", "CCO380"),
    ("Interacao Humano Computador", "CCO381"),
    ("Programacao Web", "CCO382"),
    ("Desenvolvimento Mobile", "CCO383"),
    ("Seguranca da Informacao", "CCO390"),
    ("Criptografia e Seguranca", "CCO391"),
    ("Computacao em Nuvem", "CCO392"),
    ("Sistemas Distribuidos", "CCO393"),
    ("Internet das Coisas", "CCO394"),
    ("DevOps e Observabilidade", "CCO395"),
    ("Governanca de TI", "CCO396"),
    ("Empreendedorismo em Tecnologia", "CCO397"),
    ("Etica e Legislacao em Computacao", "CCO398"),
    ("Projeto Integrador I", "CCO401"),
    ("Projeto Integrador II", "CCO402"),
    ("Topicos Avancados em Inteligencia Artificial", "CCO475"),
    ("Topicos Avancados em Ciberseguranca", "CCO476"),
    ("Topicos Avancados em Engenharia de Software", "CCO477"),
    ("Metodologia Cientifica", "MET100"),
    ("Comunicacao Tecnica", "LET101"),
    ("Ingles Instrumental para Computacao", "LET141"),
    ("Pesquisa Operacional", "MAT310"),
    ("Fundamentos de Eletronica para Computacao", "CCO213"),
    ("Trabalho de Conclusao de Curso I", "CCO490"),
    ("Trabalho de Conclusao de Curso II", "CCO491"),
    ("Estagio Supervisionado em Computacao", "CCO499"),
    ("Laboratorio de Projetos de Software", "CCO403"),
]

PRACTICAL_KEYWORDS = (
    "laboratorio",
    "programacao",
    "redes",
    "projeto",
    "sistemas distribuidos",
    "devops",
    "mobile",
    "seguranca",
    "dados",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera dados mockados em lote para Ciencia da Computacao.")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--replace-existing", action="store_true", help="Substitui todos os dados acadêmicos atuais.")
    parser.add_argument("--professores", type=int, default=100)
    parser.add_argument("--salas", type=int, default=45)
    parser.add_argument("--disciplinas", type=int, default=60)
    parser.add_argument("--alunos", type=int, default=1500)
    parser.add_argument("--timetables", type=int, default=520)
    parser.add_argument("--attendance-days", type=int, default=6)
    return parser.parse_args()


def counts() -> dict[str, int]:
    return {
        "users": User.query.count(),
        "salas": Sala.query.count(),
        "disciplinas": Disciplina.query.count(),
        "timetables": Timetable.query.count(),
        "alunos": Aluno.query.count(),
        "matriculas": Matricula.query.count(),
        "presencas": Presenca.query.count(),
    }


def recent_dates_for_weekday(weekday: int, amount: int) -> list[date]:
    today = date.today()
    delta_days = (today.weekday() - weekday) % 7
    first = today - timedelta(days=delta_days)
    return [first - timedelta(days=7 * i) for i in range(amount)]


def slug_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", ".", value.lower()).strip(".")


def is_practical_disciplina(nome: str) -> bool:
    lowered = nome.lower()
    return any(keyword in lowered for keyword in PRACTICAL_KEYWORDS)


def ensure_admin() -> None:
    admin = User.query.filter_by(role="admin").first()
    if admin:
        return

    admin = User(username="admin", email="admin@faculdade.local", role="admin")
    admin.set_password("Admin1234")
    db.session.add(admin)
    db.session.commit()


def clear_domain_data() -> None:
    Presenca.query.delete(synchronize_session=False)
    Matricula.query.delete(synchronize_session=False)
    Timetable.query.delete(synchronize_session=False)
    Aluno.query.delete(synchronize_session=False)
    Disciplina.query.delete(synchronize_session=False)
    Sala.query.delete(synchronize_session=False)
    User.query.filter(User.role == "professor").delete(synchronize_session=False)
    db.session.commit()


def create_professors(total: int) -> list[User]:
    professors: list[User] = []
    used_logins: set[str] = {u.username for u in User.query.with_entities(User.username).all()}

    for _ in range(total):
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        base = slug_name(name)
        login = f"prof.cc.{base}"
        suffix = 1
        while login in used_logins:
            suffix += 1
            login = f"prof.cc.{base}{suffix:02d}"

        used_logins.add(login)
        professor = User(
            username=login,
            email=f"{login}@dcc.universidade.br",
            role="professor",
        )
        professor.set_password("Mock12345")
        professors.append(professor)

    db.session.add_all(professors)
    db.session.commit()
    return professors


def build_room_catalog(total: int) -> list[tuple[str, int]]:
    room_catalog: list[tuple[str, int]] = []

    for bloco in ["CC1", "CC2", "CC3", "CC4"]:
        for andar in [1, 2, 3]:
            for sala in [1, 2, 3, 4, 5]:
                room_catalog.append((f"Bloco {bloco} - Sala {andar}0{sala}", random.randint(35, 60)))

    for i in range(1, 11):
        room_catalog.append((f"Laboratorio de Programacao {i:02d}", random.randint(24, 40)))

    for i in range(1, 5):
        room_catalog.append((f"Laboratorio de Redes {i:02d}", random.randint(22, 32)))

    for i in range(1, 4):
        room_catalog.append((f"Laboratorio de Hardware e IoT {i:02d}", random.randint(20, 30)))

    for i in range(1, 4):
        room_catalog.append((f"Laboratorio de IA e Ciencia de Dados {i:02d}", random.randint(20, 35)))

    for i in range(1, 4):
        room_catalog.append((f"Sala de Projetos Integradores {i:02d}", random.randint(28, 42)))

    room_catalog.extend(
        [
            ("Auditorio da Computacao", 160),
            ("Mini Auditorio Tecnologico", 90),
            ("Espaco Coworking Academico", 70),
        ]
    )

    random.shuffle(room_catalog)
    return room_catalog[:total]


def create_salas(total: int) -> list[Sala]:
    salas = [Sala(nome=nome, capacidade=capacidade) for nome, capacidade in build_room_catalog(total)]
    db.session.add_all(salas)
    db.session.commit()
    return salas


def create_disciplinas(total: int) -> list[Disciplina]:
    existing_codes = {row[0] for row in Disciplina.query.with_entities(Disciplina.codigo).all()}
    disciplinas: list[Disciplina] = []

    for idx in range(total):
        if idx < len(DISCIPLINE_CATALOG):
            nome, base_code = DISCIPLINE_CATALOG[idx]
        else:
            nome = f"Optativa de Ciencia da Computacao {idx - len(DISCIPLINE_CATALOG) + 1:02d}"
            base_code = f"CCOPT{idx:03d}"

        code = base_code
        suffix = 1
        while code in existing_codes:
            suffix += 1
            code = f"{base_code[:17]}{suffix:02d}"

        existing_codes.add(code)
        disciplinas.append(Disciplina(nome=nome, codigo=code))

    db.session.add_all(disciplinas)
    db.session.commit()
    return disciplinas


def create_alunos(total: int) -> list[Aluno]:
    alunos: list[Aluno] = []
    start_year = date.today().year - 6

    for i in range(1, total + 1):
        nome = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        ano_ingresso = random.randint(start_year, date.today().year)
        semestre_ingresso = random.choice([1, 2])
        matricula = f"{ano_ingresso}{semestre_ingresso}BCC{i:05d}"
        alunos.append(Aluno(nome=nome, matricula=matricula))

    db.session.add_all(alunos)
    db.session.commit()
    return alunos


def create_timetables(target: int, professores: list[User], salas: list[Sala], disciplinas: list[Disciplina]) -> list[Timetable]:
    created: list[Timetable] = []

    lab_rooms = [
        sala
        for sala in salas
        if "laboratorio" in sala.nome.lower() or "projetos" in sala.nome.lower() or "coworking" in sala.nome.lower()
    ]
    default_rooms = [sala for sala in salas if sala not in lab_rooms] or salas[:]

    for dia in DAYS:
        for hora_inicio, hora_fim in SLOTS:
            if len(created) >= target:
                break

            profs = professores[:]
            random.shuffle(profs)

            max_pairs = min(len(profs), len(salas))
            used_room_ids: set[int] = set()

            for professor in profs:
                if len(created) >= target or len(used_room_ids) >= max_pairs:
                    break

                disciplina = random.choice(disciplinas)
                preferred_rooms = lab_rooms if is_practical_disciplina(disciplina.nome) and lab_rooms else default_rooms

                available_rooms = [room for room in preferred_rooms if room.id not in used_room_ids]
                if not available_rooms:
                    available_rooms = [room for room in salas if room.id not in used_room_ids]
                if not available_rooms:
                    break

                room = random.choice(available_rooms)
                used_room_ids.add(room.id)

                created.append(
                    Timetable(
                        dia=dia,
                        hora_inicio=hora_inicio,
                        hora_fim=hora_fim,
                        professor_id=professor.id,
                        sala_id=room.id,
                        disciplina_id=disciplina.id,
                    )
                )

    db.session.add_all(created)
    db.session.commit()

    return (
        Timetable.query.filter(Timetable.id.in_([t.id for t in created]))
        .join(Sala, Timetable.sala_id == Sala.id)
        .all()
    )


def select_turno() -> str:
    roll = random.random()
    if roll < 0.34:
        return "matutino"
    if roll < 0.74:
        return "noturno"
    return "integral"


def matches_turno(timetable: Timetable, turno: str) -> bool:
    hour = timetable.hora_inicio.hour
    if turno == "matutino":
        return hour < 13
    if turno == "noturno":
        return hour >= 18
    return True


def create_matriculas(timetables: list[Timetable], alunos: list[Aluno]) -> list[Matricula]:
    remaining_capacity = {t.id: (t.sala.capacidade if t.sala else 30) for t in timetables}
    by_id = {t.id: t for t in timetables}

    matriculas: list[Matricula] = []

    for aluno in alunos:
        turno = select_turno()
        target = random.randint(4, 8)

        candidate_ids = [t.id for t in timetables if matches_turno(t, turno)]
        if len(candidate_ids) < target:
            candidate_ids = [t.id for t in timetables]

        random.shuffle(candidate_ids)
        used_slots: set[tuple[str, time, time]] = set()
        selected: list[int] = []

        for timetable_id in candidate_ids:
            if len(selected) >= target:
                break

            timetable = by_id[timetable_id]
            if remaining_capacity[timetable_id] <= 0:
                continue

            slot_key = (timetable.dia, timetable.hora_inicio, timetable.hora_fim)
            if slot_key in used_slots:
                continue

            used_slots.add(slot_key)
            selected.append(timetable_id)
            remaining_capacity[timetable_id] -= 1

        for timetable_id in selected:
            matriculas.append(Matricula(aluno_id=aluno.id, timetable_id=timetable_id))

    db.session.add_all(matriculas)
    db.session.commit()
    return matriculas


def create_presencas(timetables: list[Timetable], matriculas: list[Matricula], attendance_days: int) -> int:
    timetable_students: dict[int, list[int]] = defaultdict(list)
    student_attendance_profile: dict[int, float] = {}

    for matricula in matriculas:
        timetable_students[matricula.timetable_id].append(matricula.aluno_id)
        if matricula.aluno_id not in student_attendance_profile:
            student_attendance_profile[matricula.aluno_id] = random.uniform(0.68, 0.96)

    presencas: list[Presenca] = []

    for timetable in timetables:
        weekday = DAY_TO_WEEKDAY.get(timetable.dia, 0)
        attendance_dates = recent_dates_for_weekday(weekday, attendance_days)

        for aluno_id in timetable_students.get(timetable.id, []):
            base_presence = student_attendance_profile.get(aluno_id, 0.82)
            for attendance_date in attendance_dates:
                chance = min(max(base_presence + random.uniform(-0.06, 0.06), 0.4), 0.99)
                presencas.append(
                    Presenca(
                        data=attendance_date,
                        presente=random.random() < chance,
                        aluno_id=aluno_id,
                        timetable_id=timetable.id,
                    )
                )

    chunk_size = 6000
    for idx in range(0, len(presencas), chunk_size):
        db.session.add_all(presencas[idx : idx + chunk_size])
        db.session.commit()

    return len(presencas)


def main() -> None:
    args = parse_args()
    random.seed(args.seed)

    app = create_app()
    with app.app_context():
        ensure_admin()

        before = counts()
        if args.replace_existing:
            clear_domain_data()

        professores = create_professors(args.professores)
        salas = create_salas(args.salas)
        disciplinas = create_disciplinas(args.disciplinas)
        alunos = create_alunos(args.alunos)
        timetables = create_timetables(args.timetables, professores, salas, disciplinas)
        matriculas = create_matriculas(timetables, alunos)
        total_presencas = create_presencas(timetables, matriculas, args.attendance_days)

        after = counts()

        print("=== DADOS MOCK INSERIDOS ===")
        print("Cenario: Ciencia da Computacao")
        print(f"Professores criados: {len(professores)}")
        print(f"Salas criadas: {len(salas)}")
        print(f"Disciplinas criadas: {len(disciplinas)}")
        print(f"Alunos criados: {len(alunos)}")
        print(f"Turmas (timetables) criadas: {len(timetables)}")
        print(f"Matriculas criadas: {len(matriculas)}")
        print(f"Presencas criadas: {total_presencas}")

        max_possible = len(DAYS) * len(SLOTS) * min(len(professores), len(salas))
        if len(timetables) < args.timetables:
            print(
                f"Aviso: limite estrutural atingido. Solicitado={args.timetables}, criado={len(timetables)}, maximo teorico={max_possible}."
            )

        print("=== TOTAIS NO BANCO ===")
        for key in ["users", "salas", "disciplinas", "timetables", "alunos", "matriculas", "presencas"]:
            print(f"{key}: {before[key]} -> {after[key]}")


if __name__ == "__main__":
    main()
