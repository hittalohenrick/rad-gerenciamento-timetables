from __future__ import annotations

from collections import Counter
from math import ceil

from app import db
from app.forms import (
    PROFESSOR_DEFAULT_WORKLOAD,
    PROFESSOR_WORKLOAD_TURNOS,
    TURNO_CHOICES,
)
from app.models import Disciplina, GradeCurricular, GradeCurricularItem, Timetable, Turma, User

DISCIPLINAS_POR_TURMA_NOVA = 5
MAX_SLOTS_SEMANA_PROFESSOR = 20
MAX_SLOTS_POR_TURNO_PROFESSOR = 10

NOMES_BASE = [
    "ana",
    "bruno",
    "carla",
    "diego",
    "elisa",
    "fabio",
    "gabriela",
    "henrique",
    "isabela",
    "joao",
    "karina",
    "lucas",
    "mariana",
    "natan",
    "olivia",
    "paulo",
    "quiteria",
    "renato",
    "sabrina",
    "thiago",
    "ursula",
    "victor",
    "william",
    "yasmin",
    "zilda",
]
SOBRENOMES_BASE = [
    "almeida",
    "barbosa",
    "costa",
    "dias",
    "esteves",
    "ferreira",
    "gomes",
    "henrique",
    "ivanov",
    "junior",
    "klein",
    "lima",
    "moraes",
    "neves",
    "oliveira",
    "pereira",
    "queiroz",
    "rocha",
    "silva",
    "teixeira",
    "urquiza",
    "vieira",
    "watanabe",
    "xavier",
    "yamada",
    "zanetti",
]


def _infer_turno_from_hour(hour_value: int) -> str:
    if hour_value < 12:
        return "matutino"
    if hour_value < 18:
        return "vespertino"
    return "noturno"


def _active_turmas():
    return Turma.query.filter(Turma.ativa.is_(True)).all()


def _disciplinas_por_turma(turma: Turma) -> list[int]:
    rows = (
        db.session.query(GradeCurricularItem.disciplina_id)
        .join(GradeCurricular, GradeCurricular.id == GradeCurricularItem.grade_id)
        .filter(
            GradeCurricular.curso_id == turma.curso_id,
            GradeCurricular.ativa.is_(True),
            GradeCurricularItem.periodo == turma.periodo,
        )
        .distinct()
        .all()
    )
    return sorted({disciplina_id for (disciplina_id,) in rows})


def _build_demand_snapshot():
    turnos = [value for value, _ in TURNO_CHOICES]
    demand_turno = Counter({turno: 0 for turno in turnos})
    demand_disciplina = Counter()
    demand_disciplina_turno = Counter()

    timetables_rows = (
        db.session.query(Timetable.turma_id, Timetable.disciplina_id, Timetable.hora_inicio)
        .join(Turma, Turma.id == Timetable.turma_id)
        .filter(Turma.ativa.is_(True))
        .all()
    )

    turmas_by_id = {turma.id: turma for turma in _active_turmas()}
    turmas_com_quadro_ids = set()

    for turma_id, disciplina_id, hora_inicio in timetables_rows:
        turma = turmas_by_id.get(turma_id)
        if turma is None:
            continue
        turmas_com_quadro_ids.add(turma_id)
        turno = _infer_turno_from_hour(hora_inicio.hour)
        demand_turno[turno] += 1
        if disciplina_id is not None:
            demand_disciplina[disciplina_id] += 1
            demand_disciplina_turno[(turno, disciplina_id)] += 1

    turmas_sem_quadro = [turma for turma in turmas_by_id.values() if turma.id not in turmas_com_quadro_ids]
    for turma in turmas_sem_quadro:
        if turma.turno in demand_turno:
            demand_turno[turma.turno] += DISCIPLINAS_POR_TURMA_NOVA
        for disciplina_id in _disciplinas_por_turma(turma):
            demand_disciplina[disciplina_id] += 1
            demand_disciplina_turno[(turma.turno, disciplina_id)] += 1

    return {
        "demand_turno": demand_turno,
        "demand_disciplina": demand_disciplina,
        "demand_disciplina_turno": demand_disciplina_turno,
        "turmas_sem_quadro": turmas_sem_quadro,
    }


def _required_professor_profiles(demand_turno: Counter, extra_professores: int = 0) -> dict[str, int]:
    demanda_m = int(demand_turno.get("matutino", 0))
    demanda_v = int(demand_turno.get("vespertino", 0))
    demanda_n = int(demand_turno.get("noturno", 0))
    demanda_total = demanda_m + demanda_v + demanda_n

    min_ma_ve = ceil(demanda_m / MAX_SLOTS_POR_TURNO_PROFESSOR) if demanda_m else 0
    min_ve_no = ceil(demanda_n / MAX_SLOTS_POR_TURNO_PROFESSOR) if demanda_n else 0
    min_total = ceil(demanda_total / MAX_SLOTS_SEMANA_PROFESSOR) if demanda_total else 0

    target_total = max(min_total, min_ma_ve + min_ve_no)
    target_total += max(0, int(extra_professores))

    ma_ve = min_ma_ve
    ve_no = min_ve_no
    while ma_ve + ve_no < target_total:
        if demanda_m >= demanda_n:
            ma_ve += 1
        else:
            ve_no += 1

    return {
        "matutino_vespertino": ma_ve,
        "vespertino_noturno": ve_no,
        "total": target_total,
        "demanda_total": demanda_total,
    }


def _next_username(existing: set[str], sequence: int) -> str:
    base_space = len(NOMES_BASE) * len(SOBRENOMES_BASE)
    # Espalha combinacoes para evitar blocos longos com o mesmo primeiro nome.
    position = (sequence * 17 + 3) % base_space
    first_name = NOMES_BASE[position // len(SOBRENOMES_BASE)]
    last_name = SOBRENOMES_BASE[position % len(SOBRENOMES_BASE)]
    candidate = f"{first_name}.{last_name}"
    if candidate not in existing:
        return candidate

    suffix = 2
    while True:
        with_suffix = f"{candidate}{suffix}"
        if with_suffix not in existing:
            return with_suffix
        suffix += 1


def _build_professor_blueprints(profile_counts: dict[str, int]) -> list[dict[str, str]]:
    blueprints = []
    existing_usernames = {
        (username or "").strip().lower() for (username,) in db.session.query(User.username).all()
    }
    sequence = 0

    for profile_key in ["matutino_vespertino", "vespertino_noturno"]:
        qty = int(profile_counts.get(profile_key, 0))
        for _ in range(qty):
            username = _next_username(existing_usernames, sequence)
            sequence += 1
            existing_usernames.add(username)
            blueprints.append({"username": username, "profile": profile_key})

    return blueprints


def _disciplinas_curriculares():
    return (
        db.session.query(Disciplina)
        .join(GradeCurricularItem, GradeCurricularItem.disciplina_id == Disciplina.id)
        .join(GradeCurricular, GradeCurricular.id == GradeCurricularItem.grade_id)
        .filter(GradeCurricular.ativa.is_(True))
        .distinct()
        .order_by(Disciplina.nome.asc())
        .all()
    )


def _discipline_turnos_with_demand(demand_disciplina_turno: Counter, disciplina_id: int) -> set[str]:
    turnos = set()
    for (turno, current_disciplina_id), amount in demand_disciplina_turno.items():
        if current_disciplina_id == disciplina_id and amount > 0:
            turnos.add(turno)
    return turnos


def _assign_aptitudes(
    professores: list[User],
    demand_disciplina: Counter,
    demand_disciplina_turno: Counter,
    min_disciplinas_por_professor: int,
):
    disciplinas = _disciplinas_curriculares() or Disciplina.query.order_by(Disciplina.nome.asc()).all()
    if not professores or not disciplinas:
        return

    disciplina_map = {disciplina.id: disciplina for disciplina in disciplinas}
    disciplina_ids_ranked = sorted(
        disciplina_map.keys(),
        key=lambda disciplina_id: (
            -int(demand_disciplina.get(disciplina_id, 0)),
            disciplina_map[disciplina_id].nome.lower(),
        ),
    )

    min_count = max(1, min(min_disciplinas_por_professor, len(disciplina_ids_ranked)))
    professor_aptitudes: dict[int, set[int]] = {professor.id: set() for professor in professores}
    max_aptidoes = max(min_count, 12)

    for professor in professores:
        allowed_turnos = set(
            PROFESSOR_WORKLOAD_TURNOS.get(
                professor.jornada_turnos or PROFESSOR_DEFAULT_WORKLOAD,
                PROFESSOR_WORKLOAD_TURNOS[PROFESSOR_DEFAULT_WORKLOAD],
            )
        )

        scored = sorted(
            disciplina_ids_ranked,
            key=lambda disciplina_id: (
                -sum(
                    int(demand_disciplina_turno.get((turno, disciplina_id), 0))
                    for turno in allowed_turnos
                ),
                -int(demand_disciplina.get(disciplina_id, 0)),
                disciplina_map[disciplina_id].nome.lower(),
            ),
        )

        selected = []
        for disciplina_id in scored:
            selected.append(disciplina_id)
            if len(selected) >= min_count:
                break
        professor_aptitudes[professor.id] = set(selected)

    coverage = Counter()
    for disciplina_ids in professor_aptitudes.values():
        for disciplina_id in disciplina_ids:
            coverage[disciplina_id] += 1

    for disciplina_id in disciplina_ids_ranked:
        target_coverage = 2 if int(demand_disciplina.get(disciplina_id, 0)) > 0 else 1
        while coverage[disciplina_id] < target_coverage:
            turnos_demanda = _discipline_turnos_with_demand(demand_disciplina_turno, disciplina_id)
            candidates = []
            for professor in professores:
                current = professor_aptitudes[professor.id]
                if disciplina_id in current:
                    continue
                if len(current) >= max_aptidoes:
                    continue
                professor_turnos = set(
                    PROFESSOR_WORKLOAD_TURNOS.get(
                        professor.jornada_turnos or PROFESSOR_DEFAULT_WORKLOAD,
                        PROFESSOR_WORKLOAD_TURNOS[PROFESSOR_DEFAULT_WORKLOAD],
                    )
                )
                intersects = bool(turnos_demanda.intersection(professor_turnos)) if turnos_demanda else True
                candidates.append((not intersects, len(current), professor.id))

            if not candidates:
                break

            _, _, selected_professor_id = sorted(candidates)[0]
            professor_aptitudes[selected_professor_id].add(disciplina_id)
            coverage[disciplina_id] += 1

    for professor in professores:
        professor.disciplinas_aptas = [
            disciplina_map[disciplina_id]
            for disciplina_id in sorted(professor_aptitudes[professor.id])
            if disciplina_id in disciplina_map
        ]


def rebuild_professores_automatico(
    min_disciplinas_por_professor: int = 6,
    extra_professores: int = 0,
    default_password: str = "123456",
):
    snapshot = _build_demand_snapshot()
    demand_turno = snapshot["demand_turno"]
    profile_counts = _required_professor_profiles(demand_turno, extra_professores=extra_professores)
    blueprints = _build_professor_blueprints(profile_counts)

    existing_professores = User.query.filter(User.role == "professor").all()
    existing_ids = [professor.id for professor in existing_professores]
    if existing_ids:
        Timetable.query.filter(Timetable.professor_id.in_(existing_ids)).update(
            {Timetable.professor_id: None},
            synchronize_session=False,
        )
        for professor in existing_professores:
            professor.disciplinas_aptas = []
            db.session.delete(professor)
        db.session.flush()

    created_professores = []
    for blueprint in blueprints:
        user = User(
            username=blueprint["username"],
            email=f"{blueprint['username']}@login.local",
            role="professor",
            jornada_turnos=blueprint["profile"],
        )
        user.set_password(default_password)
        db.session.add(user)
        created_professores.append(user)
    db.session.flush()

    _assign_aptitudes(
        professores=created_professores,
        demand_disciplina=snapshot["demand_disciplina"],
        demand_disciplina_turno=snapshot["demand_disciplina_turno"],
        min_disciplinas_por_professor=min_disciplinas_por_professor,
    )

    db.session.commit()

    return {
        "removed_professores": len(existing_professores),
        "created_professores": len(created_professores),
        "profile_counts": {
            "matutino_vespertino": int(profile_counts.get("matutino_vespertino", 0)),
            "vespertino_noturno": int(profile_counts.get("vespertino_noturno", 0)),
        },
        "demand_turno": {
            "matutino": int(demand_turno.get("matutino", 0)),
            "vespertino": int(demand_turno.get("vespertino", 0)),
            "noturno": int(demand_turno.get("noturno", 0)),
        },
        "demanda_total": int(profile_counts.get("demanda_total", 0)),
        "min_disciplinas_por_professor": int(min_disciplinas_por_professor),
    }
