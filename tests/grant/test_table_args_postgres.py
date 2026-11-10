import pytest
from pytest_mock_resources import create_postgres_fixture
from sqlalchemy import Column, text, types

from sqlalchemy_declarative_extensions import (
    Grants,
    Roles,
    declarative_database,
    register_sqlalchemy_events,
)
from sqlalchemy_declarative_extensions.dialects.postgresql import Grant, Role
from sqlalchemy_declarative_extensions.grant.compare import compare_grants
from sqlalchemy_declarative_extensions.sqlalchemy import declarative_base

_Base = declarative_base()

reader = Role("reader")


@declarative_database
class Base(_Base):  # type: ignore
    __abstract__ = True


class Foo(Base):
    __tablename__ = "foo"
    __table_args__ = (Grant.new("select", "insert", to=reader),)

    id = Column(types.Integer(), primary_key=True)


register_sqlalchemy_events(Base.metadata, roles=True, grants=True)


_LateBase = declarative_base()


@declarative_database
class LateBase(_LateBase):  # type: ignore
    __abstract__ = True


register_sqlalchemy_events(LateBase.metadata, roles=True, grants=True)


class Baz(LateBase):
    __tablename__ = "baz"
    __table_args__ = (Grant.new("select", to=reader),)

    id = Column(types.Integer(), primary_key=True)


pg = create_postgres_fixture(scope="function", engine_kwargs={"echo": True})


@pytest.mark.grant
def test_create_all_grants_on_table(pg):
    Base.metadata.create_all(bind=pg)

    with pg.connect() as conn:
        conn.execute(text("SET ROLE reader"))
        conn.execute(text("INSERT INTO foo VALUES (1)"))
        result = conn.execute(text("SELECT id FROM foo")).scalars().all()
        conn.execute(text("RESET ROLE"))

        diff = compare_grants(
            conn, Grants.extract(Base.metadata), Roles.extract(Base.metadata)
        )

    assert result == [1]
    assert diff == []


@pytest.mark.grant
def test_grants_declared_after_registering_events(pg):
    LateBase.metadata.create_all(bind=pg)

    with pg.connect() as conn:
        conn.execute(text("SET ROLE reader"))
        result = conn.execute(text("SELECT id FROM baz")).scalars().all()

    assert result == []
