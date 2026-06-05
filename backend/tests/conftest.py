from app.db.database import init_database, seed_database


def pytest_configure() -> None:
    init_database()
    seed_database()
