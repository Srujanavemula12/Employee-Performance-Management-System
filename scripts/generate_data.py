
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from faker import Faker

SEED = 20261022
EMPLOYEE_COUNT = 3000
MANAGER_COUNT = 500

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "employee_performance.db"

fake = Faker()
Faker.seed(SEED)
random.seed(SEED)

DEPARTMENTS = [
    "Engineering", "Finance", "Human Resources",
    "Operations", "Sales", "Marketing", "IT"
]

JOB_TITLES = [
    "Software Engineer", "Data Analyst", "Business Analyst",
    "HR Specialist", "Operations Associate", "Security Analyst",
    "Project Coordinator"
]


def generate_employees(connection):
    today = date(2026, 10, 22)
    rows = []

    for i in range(1, EMPLOYEE_COUNT + 1):
        hire_date = today - timedelta(days=random.randint(30, 3650))
        rows.append((
            f"EMP-{i:06d}",
            fake.first_name(),
            fake.last_name(),
            f"employee{i:06d}@example.com",
            random.choice(DEPARTMENTS),
            random.choice(JOB_TITLES),
            hire_date.isoformat(),
            "ACTIVE",
            None,
            hire_date.isoformat(),
            None
        ))

    connection.executemany(
        """
        INSERT INTO employees (
            employee_id, first_name, last_name, email,
            department, job_title, hire_date, employment_status,
            manager_id, effective_from, effective_to
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows
    )

    print(f"Employees generated: {len(rows)}")


def generate_managers(connection):
    rows = []

    for i in range(1, MANAGER_COUNT + 1):
        rows.append((
            f"MGR-{i:04d}",
            f"EMP-{i:06d}",
            random.choice([
                "TEAM_LEAD", "MANAGER",
                "SENIOR_MANAGER", "DIRECTOR"
            ]),
            f"Team-{i:03d}",
            "2024-01-01",
            None
        ))

    connection.executemany(
        """
        INSERT INTO managers (
            manager_id, employee_id, management_level,
            team_name, effective_from, effective_to
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        rows
    )

    print(f"Managers generated: {len(rows)}")


def generate_review_cycles(connection):
    cycles = [
        (
            "CYCLE-2026-H1", "2026 H1",
            "2026-01-01", "2026-06-30",
            "2026-06-15", "2026-06-25", "CLOSED",
            "2026-07-01"
        ),
        (
            "CYCLE-2026-H2", "2026 H2",
            "2026-07-01", "2026-12-31",
            "2026-12-15", "2026-12-25", "ACTIVE",
            None
        )
    ]

    connection.executemany(
        """
        INSERT INTO review_cycles (
            cycle_id, cycle_name, start_date, end_date,
            self_review_deadline, manager_review_deadline,
            status, closed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        cycles
    )

    print(f"Review cycles generated: {len(cycles)}")


def generate_competencies(connection):
    competencies = [
        ("COMP-001", "Technical Skills", "Role-related technical expertise", "TECHNICAL"),
        ("COMP-002", "Communication", "Clear and effective communication", "COMMUNICATION"),
        ("COMP-003", "Leadership", "Guidance and decision-making", "LEADERSHIP"),
        ("COMP-004", "Teamwork", "Collaboration with others", "TEAMWORK"),
        ("COMP-005", "Problem Solving", "Analysis and resolution of problems", "TECHNICAL")
    ]

    connection.executemany(
        """
        INSERT INTO competencies (
            competency_id, competency_name, description, category
        ) VALUES (?, ?, ?, ?)
        """,
        competencies
    )

    print(f"Competencies generated: {len(competencies)}")


def main():
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        existing = connection.execute(
            "SELECT COUNT(*) FROM employees"
        ).fetchone()[0]

        if existing:
            raise RuntimeError(
                "Employees already exist. Refusing to duplicate data. "
                "Use a fresh database if you want to regenerate."
            )

        generate_employees(connection)
        generate_managers(connection)
        generate_review_cycles(connection)
        generate_competencies(connection)

    print("Master data generation completed.")


if __name__ == "__main__":
    main()