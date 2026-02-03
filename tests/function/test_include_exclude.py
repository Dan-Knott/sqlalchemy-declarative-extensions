import pytest
from pytest_mock_resources import create_postgres_fixture
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from sqlalchemy_declarative_extensions import (
    Functions,
    declarative_database,
    register_sqlalchemy_events,
)
from sqlalchemy_declarative_extensions.sqlalchemy import declarative_base

_Base = declarative_base()


@declarative_database
class BaseIncludeOnly(_Base):  # type: ignore
    __abstract__ = True

    functions = Functions(include=["test_*"])


@declarative_database
class BaseExcludeOnly(_Base):  # type: ignore
    __abstract__ = True

    functions = Functions(ignore=["ignore_*"])


@declarative_database
class BaseIncludeAndExclude(_Base):  # type: ignore
    __abstract__ = True

    functions = Functions(include=["test_*", "keep_*"], ignore=["*_ignore"])


register_sqlalchemy_events(BaseIncludeOnly.metadata, functions=True)
register_sqlalchemy_events(BaseExcludeOnly.metadata, functions=True)
register_sqlalchemy_events(BaseIncludeAndExclude.metadata, functions=True)

pg_include = create_postgres_fixture(engine_kwargs={"echo": True}, session=True)
pg_exclude = create_postgres_fixture(engine_kwargs={"echo": True}, session=True)
pg_both = create_postgres_fixture(engine_kwargs={"echo": True}, session=True)


def test_include_only(pg_include):
    # Matches the include pattern, thus dropped because it's not declared.
    pg_include.execute(
        text(
            "CREATE FUNCTION test_func() RETURNS INTEGER language sql as $$ select 1 $$;"
        )
    )
    # Doesn't match the include pattern, thus kept because it's unmanaged.
    pg_include.execute(
        text(
            "CREATE FUNCTION other_func() RETURNS INTEGER language sql as $$ select 2 $$;"
        )
    )
    pg_include.commit()

    BaseIncludeOnly.metadata.create_all(bind=pg_include.connection())
    pg_include.commit()

    with pytest.raises(ProgrammingError):
        pg_include.execute(text("SELECT test_func()")).scalar()
    pg_include.rollback()

    result = pg_include.execute(text("SELECT other_func()")).scalar()
    assert result == 2


def test_exclude_only(pg_exclude):
    # Matches the exclude pattern, thus kept because it's being ignored.
    pg_exclude.execute(
        text(
            "CREATE FUNCTION ignore_this() RETURNS INTEGER language sql as $$ select 1 $$;"
        )
    )
    # Doesn't match the exclude pattern, thus dropped because it's not being ignored.
    pg_exclude.execute(
        text(
            "CREATE FUNCTION manage_this() RETURNS INTEGER language sql as $$ select 2 $$;"
        )
    )
    pg_exclude.commit()

    BaseExcludeOnly.metadata.create_all(bind=pg_exclude.connection())
    pg_exclude.commit()

    result = pg_exclude.execute(text("SELECT ignore_this()")).scalar()
    assert result == 1

    with pytest.raises(ProgrammingError):
        pg_exclude.execute(text("SELECT manage_this()")).scalar()


def test_include_and_exclude_interaction(pg_both):
    """Test the interaction between include and exclude.

    A function that matches include becomes managed, but can become unmanaged if also matching the
    exclude.
    """
    pg_both.execute(
        text(
            "CREATE FUNCTION test_func() RETURNS INTEGER language sql as $$ select 1 $$;"
        )
    )
    pg_both.execute(
        text(
            "CREATE FUNCTION test_ignore() RETURNS INTEGER language sql as $$ select 2 $$;"
        )
    )
    pg_both.execute(
        text(
            "CREATE FUNCTION keep_this() RETURNS INTEGER language sql as $$ select 3 $$;"
        )
    )
    pg_both.execute(
        text(
            "CREATE FUNCTION other_func() RETURNS INTEGER language sql as $$ select 4 $$;"
        )
    )

    pg_both.commit()

    BaseIncludeAndExclude.metadata.create_all(bind=pg_both.connection())
    pg_both.commit()

    with pytest.raises(ProgrammingError):
        pg_both.execute(text("SELECT test_func()")).scalar()
    pg_both.rollback()

    result = pg_both.execute(text("SELECT test_ignore()")).scalar()
    assert result == 2

    with pytest.raises(ProgrammingError):
        pg_both.execute(text("SELECT keep_this()")).scalar()
    pg_both.rollback()

    result = pg_both.execute(text("SELECT other_func()")).scalar()
    assert result == 4


def test_include_with_schema_patterns(pg_include):
    pg_include.execute(text("CREATE SCHEMA foo"))
    pg_include.execute(text("CREATE SCHEMA bar"))

    pg_include.execute(
        text(
            "CREATE FUNCTION test_one() RETURNS INTEGER language sql as $$ select 1 $$;"
        )
    )
    pg_include.execute(
        text(
            "CREATE FUNCTION foo.test_two() RETURNS INTEGER language sql as $$ select 2 $$;"
        )
    )
    pg_include.execute(
        text(
            "CREATE FUNCTION bar.other() RETURNS INTEGER language sql as $$ select 3 $$;"
        )
    )

    pg_include.commit()

    BaseIncludeOnly.metadata.create_all(bind=pg_include.connection())
    pg_include.commit()

    with pytest.raises(ProgrammingError):
        pg_include.execute(text("SELECT test_one()")).scalar()
    pg_include.rollback()

    result = pg_include.execute(text("SELECT foo.test_two()")).scalar()
    assert result == 2

    result = pg_include.execute(text("SELECT bar.other()")).scalar()
    assert result == 3
