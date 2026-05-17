from __future__ import annotations

import argparse

from app import create_app, db
from app.services.professor_planner import rebuild_professores_automatico


def parse_args():
    parser = argparse.ArgumentParser(
        description="Replaneja automaticamente o corpo docente (quantidade, jornada e aptidoes)."
    )
    parser.add_argument(
        "--min-disciplinas",
        type=int,
        default=6,
        help="Quantidade minima de disciplinas aptas por professor.",
    )
    parser.add_argument(
        "--extra-professores",
        type=int,
        default=0,
        help="Reserva adicional de professores alem do minimo necessario.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    app = create_app()
    with app.app_context():
        db.create_all()
        summary = rebuild_professores_automatico(
            min_disciplinas_por_professor=max(1, args.min_disciplinas),
            extra_professores=max(0, args.extra_professores),
        )
        print("=== Replanejamento Docente ===")
        print(f"Professores removidos: {summary['removed_professores']}")
        print(f"Professores criados: {summary['created_professores']}")
        print(
            "Distribuicao de jornada: "
            f"matutino+vespertino={summary['profile_counts']['matutino_vespertino']}, "
            f"vespertino+noturno={summary['profile_counts']['vespertino_noturno']}"
        )
        print(
            "Demanda planejada de slots por turno: "
            f"matutino={summary['demand_turno']['matutino']}, "
            f"vespertino={summary['demand_turno']['vespertino']}, "
            f"noturno={summary['demand_turno']['noturno']}"
        )
        print(f"Demanda total de slots: {summary['demanda_total']}")
        print(f"Minimo de disciplinas aptas por professor: {summary['min_disciplinas_por_professor']}")


if __name__ == "__main__":
    main()
