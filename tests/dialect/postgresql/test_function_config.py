import pytest
from pytest_mock_resources import create_postgres_fixture
from sqlalchemy import text

from sqlalchemy_declarative_extensions import Functions, Procedures
from sqlalchemy_declarative_extensions.dialects.postgresql import (
    Function,
    FunctionSecurity,
    Procedure,
)
from sqlalchemy_declarative_extensions.dialects.postgresql.query import (
    get_functions_postgresql,
)
from sqlalchemy_declarative_extensions.function.compare import (
    UpdateFunctionOp,
    compare_functions,
)
from sqlalchemy_declarative_extensions.procedure.compare import compare_procedures

pg = create_postgres_fixture(scope="function", engine_kwargs={"echo": True})


def add(**attributes):
    return Function(
        name="add",
        definition="SELECT a + b;",
        parameters=["a integer", "b integer"],
        returns="INTEGER",
        **attributes,
    )


@pytest.mark.parametrize(
    "config",
    [
        None,
        {"search_path": "public"},
        {"search_path": "public, pg_temp"},
        {"search_path": '"$user", public'},
        {"enable_seqscan": "off"},
        {"statement_timeout": "5000", "search_path": "pg_temp, public"},
    ],
)
def test_function_config(pg, config):
    add_function = add(config=config).normalize()
    functions = Functions([add_function])
    with pg.connect() as connection:
        connection.execute(text("\n".join(add_function.to_sql_create())))
        diff = compare_functions(connection, functions)
    assert diff == []


def test_function_security_definer_search_path(pg):
    add_function = add(
        security=FunctionSecurity.definer,
        config={"search_path": "public, pg_temp"},
    ).normalize()
    functions = Functions([add_function])
    with pg.connect() as connection:
        connection.execute(text("\n".join(add_function.to_sql_create())))
        diff = compare_functions(connection, functions)
    assert diff == []


def test_function_config_emitted_verbatim():
    add_function = add(
        config={"statement_timeout": "5000", "search_path": '"$user", public'}
    ).normalize()
    assert add_function.to_sql_create() == [
        'CREATE FUNCTION "add"(a int4, b int4) RETURNS int4'
        ' SET "search_path" TO "$user", public'
        ' SET "statement_timeout" TO 5000'
        " LANGUAGE sql AS $$SELECT a + b;$$;"
    ]


@pytest.mark.parametrize(
    "config",
    [
        None,
        {"search_path": "public, pg_temp"},
        {"enable_seqscan": "off"},
    ],
)
def test_procedure_config(pg, config):
    noop_procedure = Procedure(
        name="noop",
        definition="BEGIN END;",
        language="plpgsql",
        config=config,
    ).normalize()
    procedures = Procedures([noop_procedure])
    with pg.connect() as connection:
        connection.execute(text("\n".join(noop_procedure.to_sql_create())))
        diff = compare_procedures(connection, procedures)
    assert diff == []


def test_function_config_from_current(pg):
    with pg.connect() as connection:
        search_path = connection.execute(text("SHOW search_path")).scalar()
        connection.execute(
            text(
                "CREATE FUNCTION add(a integer, b integer) RETURNS INTEGER"
                " SET search_path FROM CURRENT LANGUAGE sql AS $$SELECT a + b;$$"
            )
        )

        existing = {f.name: f for f in get_functions_postgresql(connection)}
        assert existing["add"].config == {"search_path": search_path}

        diff = compare_functions(
            connection, Functions([add(config={"search_path": search_path})])
        )
    assert diff == []


def test_function_config_from_current_always_diffs(pg):
    with pg.connect() as connection:
        connection.execute(text("SET search_path TO public, pg_temp"))
        connection.execute(
            text(
                "CREATE FUNCTION add(a integer, b integer) RETURNS INTEGER"
                " SET search_path FROM CURRENT LANGUAGE sql AS $$SELECT a + b;$$"
            )
        )

        unset = compare_functions(connection, Functions([add()]))
        mismatched = compare_functions(
            connection, Functions([add(config={"search_path": "public"})])
        )

    for diff in (unset, mismatched):
        assert len(diff) == 1
        assert isinstance(diff[0], UpdateFunctionOp)
        assert diff[0].from_function.config == {"search_path": "public, pg_temp"}
