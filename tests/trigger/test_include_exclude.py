from pytest_mock_resources import create_postgres_fixture
from sqlalchemy import Column, text, types

from sqlalchemy_declarative_extensions import (
    Triggers,
    declarative_database,
    register_sqlalchemy_events,
)
from sqlalchemy_declarative_extensions.sqlalchemy import declarative_base

_Base = declarative_base()


@declarative_database
class BaseIncludeOnly(_Base):  # type: ignore
    __abstract__ = True

    triggers = Triggers(include=["test_*"])


@declarative_database
class BaseExcludeOnly(_Base):  # type: ignore
    __abstract__ = True

    triggers = Triggers(ignore=["ignore_*"])


@declarative_database
class BaseIncludeAndExclude(_Base):  # type: ignore
    __abstract__ = True

    triggers = Triggers(include=["test_*", "keep_*"], ignore=["*_ignore"])


class Foo(BaseIncludeOnly):
    __tablename__ = "foo"
    id = Column(types.Integer(), primary_key=True)


class Bar(BaseExcludeOnly):
    __tablename__ = "bar"
    id = Column(types.Integer(), primary_key=True)


class Baz(BaseIncludeAndExclude):
    __tablename__ = "baz"
    id = Column(types.Integer(), primary_key=True)


register_sqlalchemy_events(BaseIncludeOnly.metadata, triggers=True)
register_sqlalchemy_events(BaseExcludeOnly.metadata, triggers=True)
register_sqlalchemy_events(BaseIncludeAndExclude.metadata, triggers=True)

pg_include = create_postgres_fixture(engine_kwargs={"echo": True}, session=True)
pg_exclude = create_postgres_fixture(engine_kwargs={"echo": True}, session=True)
pg_both = create_postgres_fixture(engine_kwargs={"echo": True}, session=True)


def test_include_only(pg_include):
    pg_include.execute(text("CREATE TABLE foo (id integer primary key);"))
    pg_include.execute(
        text(
            """
            CREATE FUNCTION trigger_func() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
            RETURN NEW;
            END
            $$;
            """
        )
    )
    pg_include.execute(
        text(
            "CREATE TRIGGER test_trigger AFTER INSERT ON foo FOR EACH ROW EXECUTE PROCEDURE trigger_func();"
        )
    )
    pg_include.execute(
        text(
            "CREATE TRIGGER other_trigger AFTER INSERT ON foo FOR EACH ROW EXECUTE PROCEDURE trigger_func();"
        )
    )

    pg_include.commit()

    BaseIncludeOnly.metadata.create_all(bind=pg_include.connection())
    pg_include.commit()

    result = pg_include.execute(
        text(
            "SELECT trigger_name FROM information_schema.triggers WHERE trigger_schema = 'public'"
        )
    ).fetchall()

    trigger_names = [r[0] for r in result]
    assert "test_trigger" not in trigger_names
    assert "other_trigger" in trigger_names


def test_exclude_only(pg_exclude):
    pg_exclude.execute(text("CREATE TABLE bar (id integer primary key);"))
    pg_exclude.execute(
        text(
            """
            CREATE FUNCTION trigger_func() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
            RETURN NEW;
            END
            $$;
            """
        )
    )
    pg_exclude.execute(
        text(
            "CREATE TRIGGER ignore_this AFTER INSERT ON bar FOR EACH ROW EXECUTE PROCEDURE trigger_func();"
        )
    )
    pg_exclude.execute(
        text(
            "CREATE TRIGGER manage_this AFTER INSERT ON bar FOR EACH ROW EXECUTE PROCEDURE trigger_func();"
        )
    )

    pg_exclude.commit()

    BaseExcludeOnly.metadata.create_all(bind=pg_exclude.connection())
    pg_exclude.commit()

    result = pg_exclude.execute(
        text(
            "SELECT trigger_name FROM information_schema.triggers WHERE trigger_schema = 'public'"
        )
    ).fetchall()

    trigger_names = [r[0] for r in result]
    assert "ignore_this" in trigger_names
    assert "manage_this" not in trigger_names


def test_include_and_exclude_interaction(pg_both):
    pg_both.execute(text("CREATE TABLE baz (id integer primary key);"))
    pg_both.execute(
        text(
            """
            CREATE FUNCTION trigger_func() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
            RETURN NEW;
            END
            $$;
            """
        )
    )
    pg_both.execute(
        text(
            "CREATE TRIGGER test_trigger AFTER INSERT ON baz FOR EACH ROW EXECUTE PROCEDURE trigger_func();"
        )
    )
    pg_both.execute(
        text(
            "CREATE TRIGGER test_ignore AFTER INSERT ON baz FOR EACH ROW EXECUTE PROCEDURE trigger_func();"
        )
    )
    pg_both.execute(
        text(
            "CREATE TRIGGER keep_this AFTER INSERT ON baz FOR EACH ROW EXECUTE PROCEDURE trigger_func();"
        )
    )
    pg_both.execute(
        text(
            "CREATE TRIGGER other_trigger AFTER INSERT ON baz FOR EACH ROW EXECUTE PROCEDURE trigger_func();"
        )
    )

    pg_both.commit()

    BaseIncludeAndExclude.metadata.create_all(bind=pg_both.connection())
    pg_both.commit()

    result = pg_both.execute(
        text(
            "SELECT trigger_name FROM information_schema.triggers WHERE trigger_schema = 'public'"
        )
    ).fetchall()

    trigger_names = [r[0] for r in result]
    assert "test_trigger" not in trigger_names
    assert "test_ignore" in trigger_names
    assert "keep_this" not in trigger_names
    assert "other_trigger" in trigger_names
