import pytest
from sqlalchemy import text

from app.db.session import engine
from app.seed_categories import main as seed_categories
from app.seed_roles import main as seed_roles
from app.seed_service_categories import main as seed_service_categories


@pytest.fixture(scope="session")
def database_available() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@pytest.fixture
def seeded_db(database_available: bool):
    if not database_available:
        pytest.skip("PostgreSQL not available (start Docker: docker compose up -d)")
    seed_roles()
    seed_categories()
    seed_service_categories()
    yield