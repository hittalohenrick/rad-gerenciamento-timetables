from __future__ import annotations

from collections.abc import Iterable
import unicodedata

from app import create_app, db
from app.models import Curso, Disciplina, GradeCurricular, GradeCurricularItem, Turma
from sqlalchemy import func, or_


GRADE_NAME = "Grade Base 2026"


CURRICULA: dict[str, dict[str, object]] = {
    "ES": {
        "nome": "Engenharia de Software",
        "quantidade_periodos": 10,
        "periodos": {
            1: [
                "Algoritmos e Logica de Programacao",
                "Fundamentos de Computacao",
                "Matematica Discreta",
                "Calculo I",
                "Comunicacao Tecnica",
            ],
            2: [
                "Programacao Orientada a Objetos",
                "Estruturas de Dados I",
                "Arquitetura de Computadores",
                "Calculo II",
                "Algebra Linear",
            ],
            3: [
                "Estruturas de Dados II",
                "Banco de Dados I",
                "Sistemas Operacionais",
                "Probabilidade e Estatistica",
                "Engenharia de Requisitos",
            ],
            4: [
                "Banco de Dados II",
                "Redes de Computadores",
                "Analise e Projeto de Algoritmos",
                "Interacao Humano-Computador",
                "Arquitetura de Software",
            ],
            5: [
                "Engenharia de Software I (Processos)",
                "Programacao Web",
                "Padroes de Projeto",
                "Testes de Software",
                "Gestao de Projetos de Software",
            ],
            6: [
                "Engenharia de Software II (Qualidade)",
                "DevOps e CI-CD",
                "Seguranca de Software",
                "Sistemas Distribuidos",
                "Desenvolvimento Mobile",
            ],
            7: [
                "Engenharia de Software III (Manutencao e Evolucao)",
                "Computacao em Nuvem",
                "Microsservicos e APIs",
                "Governanca e Metricas de TI",
                "Empreendedorismo e Inovacao",
            ],
            8: [
                "Engenharia de Dados",
                "Observabilidade e SRE",
                "UX Avancado",
                "Qualidade e Automacao de Testes",
                "Projeto Integrador I",
            ],
            9: [
                "Arquitetura Corporativa",
                "Topicos Avancados em Engenharia de Software",
                "Direito Digital e LGPD",
                "Optativa I - ES",
                "TCC I - ES",
            ],
            10: [
                "Gestao de Produto Digital",
                "Auditoria e Conformidade de Software",
                "Optativa II - ES",
                "Estagio Supervisionado - ES",
                "TCC II - ES",
            ],
        },
    },
    "CC": {
        "nome": "Ciencia da Computacao",
        "quantidade_periodos": 8,
        "periodos": {
            1: [
                "Algoritmos e Programacao I",
                "Fundamentos de Computacao",
                "Matematica Discreta",
                "Calculo I",
                "Comunicacao Cientifica",
            ],
            2: [
                "Algoritmos e Programacao II (OO)",
                "Estruturas de Dados I",
                "Arquitetura de Computadores",
                "Calculo II",
                "Algebra Linear",
            ],
            3: [
                "Estruturas de Dados II",
                "Linguagens Formais e Automatos",
                "Sistemas Operacionais",
                "Probabilidade e Estatistica",
                "Banco de Dados I",
            ],
            4: [
                "Teoria da Computacao",
                "Analise de Algoritmos",
                "Redes de Computadores",
                "Banco de Dados II",
                "Paradigmas de Programacao",
            ],
            5: [
                "Compiladores",
                "Inteligencia Artificial",
                "Engenharia de Software",
                "Computacao Grafica",
                "Metodos Numericos",
            ],
            6: [
                "Sistemas Distribuidos",
                "Aprendizado de Maquina",
                "Seguranca da Informacao",
                "Interacao Humano-Computador",
                "Pesquisa Operacional",
            ],
            7: [
                "Computacao em Nuvem",
                "Mineracao de Dados",
                "Otimizacao Combinatoria",
                "Empreendedorismo em Tecnologia",
                "TCC I - CC",
            ],
            8: [
                "Processamento de Imagens e Visao Computacional",
                "Sistemas Embarcados",
                "Direito Digital e LGPD",
                "Optativa - CC",
                "TCC II - CC",
            ],
        },
    },
    "ADS": {
        "nome": "Analise e Desenvolvimento de Sistemas",
        "quantidade_periodos": 5,
        "periodos": {
            1: [
                "Logica de Programacao",
                "Fundamentos de Computacao",
                "Modelagem de Processos de Negocio",
                "Banco de Dados I",
                "Engenharia de Requisitos",
            ],
            2: [
                "Programacao Orientada a Objetos",
                "Estruturas de Dados",
                "Banco de Dados II",
                "Desenvolvimento Web I",
                "Sistemas Operacionais e Redes",
            ],
            3: [
                "Analise e Projeto de Sistemas",
                "Desenvolvimento Web II",
                "APIs e Integracao de Sistemas",
                "Testes de Software",
                "UX-UI e IHC",
            ],
            4: [
                "Arquitetura de Software e Padroes",
                "Desenvolvimento Mobile",
                "Gestao Agil de Projetos",
                "Seguranca de Aplicacoes",
                "DevOps e CI-CD",
            ],
            5: [
                "Projeto Integrador (Capstone)",
                "Qualidade e Metricas de Software",
                "Empreendedorismo e Inovacao",
                "Governanca de TI",
                "Estagio ou TCC - ADS",
            ],
        },
    },
}


def normalize(value: str) -> str:
    return (value or "").strip().lower()


def fold_name(value: str) -> str:
    normalized = unicodedata.normalize("NFD", normalize(value))
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def validate_curricula():
    for codigo, payload in CURRICULA.items():
        quantidade_periodos = int(payload["quantidade_periodos"])
        periodos: dict[int, list[str]] = payload["periodos"]  # type: ignore[assignment]

        if len(periodos) != quantidade_periodos:
            raise ValueError(
                f"{codigo}: quantidade_periodos={quantidade_periodos}, mas foram definidos {len(periodos)} periodos."
            )

        for periodo in range(1, quantidade_periodos + 1):
            if periodo not in periodos:
                raise ValueError(f"{codigo}: periodo {periodo} nao definido.")
            disciplinas = periodos[periodo]
            if len(disciplinas) != 5:
                raise ValueError(
                    f"{codigo}: periodo {periodo} precisa ter 5 disciplinas (atual: {len(disciplinas)})."
                )
            if len({normalize(nome) for nome in disciplinas}) != len(disciplinas):
                raise ValueError(f"{codigo}: disciplinas duplicadas no periodo {periodo}.")

        disciplinas_flat: list[str] = [nome for nomes in periodos.values() for nome in nomes]
        if len({normalize(nome) for nome in disciplinas_flat}) != len(disciplinas_flat):
            raise ValueError(
                f"{codigo}: a grade possui disciplina repetida em periodos diferentes; no modelo atual isso nao e permitido."
            )


def next_disciplina_code(existing_codes: set[str]) -> str:
    idx = 1
    while True:
        code = f"DISC{idx:04d}"
        idx += 1
        if code not in existing_codes:
            return code


def ensure_disciplinas(names: Iterable[str]) -> tuple[dict[str, Disciplina], int]:
    existing_by_norm = {
        normalize(disciplina.nome): disciplina
        for disciplina in Disciplina.query.all()
    }
    existing_codes = {
        codigo for (codigo,) in db.session.query(Disciplina.codigo).all()
    }

    created = 0
    for nome in names:
        key = normalize(nome)
        if key in existing_by_norm:
            continue
        disciplina = Disciplina(nome=nome, codigo=next_disciplina_code(existing_codes))
        existing_codes.add(disciplina.codigo)
        db.session.add(disciplina)
        db.session.flush()
        existing_by_norm[key] = disciplina
        created += 1

    return existing_by_norm, created


def ensure_curso(codigo: str, nome: str, quantidade_periodos: int) -> tuple[Curso, bool]:
    curso = Curso.query.filter_by(codigo=codigo).first()
    if curso is None:
        target_folded_name = fold_name(nome)
        for existing in Curso.query.order_by(Curso.id.asc()).all():
            if fold_name(existing.nome) == target_folded_name:
                curso = existing
                break

    created = False
    if curso is None:
        curso = Curso(
            codigo=codigo,
            nome=nome,
            quantidade_periodos=quantidade_periodos,
            ativo=True,
        )
        db.session.add(curso)
        db.session.flush()
        created = True
    else:
        curso.codigo = codigo
        curso.nome = nome
        curso.quantidade_periodos = quantidade_periodos
        curso.ativo = True
    return curso, created


def ensure_grade(curso: Curso) -> tuple[GradeCurricular, bool]:
    grade = GradeCurricular.query.filter_by(curso_id=curso.id, nome=GRADE_NAME).first()
    created = False
    if grade is None:
        grade = GradeCurricular(curso_id=curso.id, nome=GRADE_NAME, ativa=True)
        db.session.add(grade)
        db.session.flush()
        created = True

    GradeCurricular.query.filter(
        GradeCurricular.curso_id == curso.id,
        GradeCurricular.id != grade.id,
    ).update({"ativa": False})
    grade.ativa = True
    return grade, created


def load_curricula():
    validate_curricula()

    all_disciplina_names: list[str] = []
    for payload in CURRICULA.values():
        periodos: dict[int, list[str]] = payload["periodos"]  # type: ignore[assignment]
        for disciplinas in periodos.values():
            all_disciplina_names.extend(disciplinas)

    disciplina_by_norm, disciplinas_created = ensure_disciplinas(all_disciplina_names)
    cursos_created = 0
    cursos_deleted = 0
    grades_created = 0
    grade_items_created = 0
    grade_items_replaced = 0

    for codigo, payload in CURRICULA.items():
        curso_nome = str(payload["nome"])
        quantidade_periodos = int(payload["quantidade_periodos"])
        periodos: dict[int, list[str]] = payload["periodos"]  # type: ignore[assignment]

        curso, created_curso = ensure_curso(codigo, curso_nome, quantidade_periodos)
        if created_curso:
            cursos_created += 1

        grade, created_grade = ensure_grade(curso)
        if created_grade:
            grades_created += 1

        grade_items_replaced += GradeCurricularItem.query.filter_by(grade_id=grade.id).count()
        GradeCurricularItem.query.filter_by(grade_id=grade.id).delete()

        for periodo in range(1, quantidade_periodos + 1):
            for disciplina_nome in periodos[periodo]:
                disciplina = disciplina_by_norm[normalize(disciplina_nome)]
                db.session.add(
                    GradeCurricularItem(
                        grade_id=grade.id,
                        disciplina_id=disciplina.id,
                        periodo=periodo,
                    )
                )
                grade_items_created += 1

    target_codes = set(CURRICULA.keys())
    for curso in Curso.query.order_by(Curso.id.asc()).all():
        if curso.codigo in target_codes:
            continue
        has_turmas = Turma.query.filter_by(curso_id=curso.id).count() > 0
        has_grades = GradeCurricular.query.filter_by(curso_id=curso.id).count() > 0
        if not has_turmas and not has_grades:
            db.session.delete(curso)
            cursos_deleted += 1
        else:
            curso.ativo = False

    db.session.commit()

    print("=== Carga Curricular Base ===")
    print(f"Disciplinas criadas: {disciplinas_created}")
    print(f"Cursos criados: {cursos_created}")
    print(f"Cursos legados removidos: {cursos_deleted}")
    print(f"Grades criadas: {grades_created}")
    print(f"Itens de grade substituidos: {grade_items_replaced}")
    print(f"Itens de grade inseridos: {grade_items_created}")
    print("--- Totais ---")
    print(f"Cursos: {Curso.query.count()}")
    print(f"Disciplinas: {Disciplina.query.count()}")
    print(f"Grades: {GradeCurricular.query.count()} (ativas: {GradeCurricular.query.filter_by(ativa=True).count()})")
    print(f"Itens de grade: {GradeCurricularItem.query.count()}")


def main():
    app = create_app()
    with app.app_context():
        db.create_all()
        load_curricula()


if __name__ == "__main__":
    main()
