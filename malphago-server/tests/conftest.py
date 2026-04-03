"""Test configuration and fixtures."""

import asyncio
from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from httpx import AsyncClient, ASGITransport

from app.db.base import Base
from app.models.track import Track
from app.models.horse import Horse
from app.models.jockey import Jockey
from app.models.trainer import Trainer
from app.models.race import Race
from app.models.race_entry import RaceEntry
from app.models.race_timing import RaceTiming
from app.models.prediction import Prediction
from app.models.entry_change_log import EntryChangeLog


# SQLite async for tests
TEST_DB_URL = "sqlite+aiosqlite:///file::memory:?cache=shared&uri=true"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
test_session_factory = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest_asyncio.fixture
async def db_session():
    """Create tables and provide a test session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with test_session_factory() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def seeded_session(db_session: AsyncSession):
    """DB session with seed data for testing."""
    # Tracks
    track_s = Track(id=1, code="S", name="서울", name_en="Seoul")
    track_b = Track(id=2, code="B", name="부산", name_en="Busan")
    db_session.add_all([track_s, track_b])

    # Horses
    horses = [
        Horse(id=1, name="번개호"),
        Horse(id=2, name="질풍이"),
        Horse(id=3, name="드림윈"),
    ]
    db_session.add_all(horses)

    # Jockeys
    jockeys = [
        Jockey(id=1, name="김동수"),
        Jockey(id=2, name="박재현"),
    ]
    db_session.add_all(jockeys)

    # Trainers
    trainers = [
        Trainer(id=1, name="이영호"),
        Trainer(id=2, name="김수일"),
    ]
    db_session.add_all(trainers)

    # Race
    race = Race(
        id=1,
        track_id=1,
        race_date=date(2025, 4, 19),
        race_number=3,
        race_name="국3",
        distance=1400,
        total_entries=3,
    )
    db_session.add(race)

    # Entries with results
    entries = [
        RaceEntry(
            id=1, race_id=1, horse_id=1, jockey_id=1, trainer_id=1,
            horse_number=1, ranking=1, favor_ranking=2, rating=72,
        ),
        RaceEntry(
            id=2, race_id=1, horse_id=2, jockey_id=2, trainer_id=2,
            horse_number=2, ranking=3, favor_ranking=1, rating=68,
        ),
        RaceEntry(
            id=3, race_id=1, horse_id=3, jockey_id=1, trainer_id=2,
            horse_number=3, ranking=5, favor_ranking=5, rating=65,
            race_interval=30,
        ),
    ]
    db_session.add_all(entries)

    # Extra historical race for richer statistics
    race2 = Race(
        id=2, track_id=1, race_date=date(2025, 4, 12),
        race_number=5, distance=1200, total_entries=2,
    )
    db_session.add(race2)
    hist_entries = [
        RaceEntry(
            id=4, race_id=2, horse_id=1, jockey_id=1, trainer_id=1,
            horse_number=1, ranking=2, favor_ranking=1, rating=70,
        ),
        RaceEntry(
            id=5, race_id=2, horse_id=2, jockey_id=2, trainer_id=2,
            horse_number=2, ranking=1, favor_ranking=2, rating=69,
        ),
    ]
    db_session.add_all(hist_entries)

    await db_session.commit()
    yield db_session


@pytest_asyncio.fixture
async def client(seeded_session: AsyncSession):
    """Test HTTP client with dependency override."""
    from app.main import app
    from app.db.session import get_db
    from app.services.scheduler import start_scheduler, stop_scheduler

    async def override_get_db():
        yield seeded_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
