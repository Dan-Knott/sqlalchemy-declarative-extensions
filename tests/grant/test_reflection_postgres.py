import pytest
from pytest_mock_resources import create_postgres_fixture
from sqlalchemy import text

from sqlalchemy_declarative_extensions import Grants, Roles
from sqlalchemy_declarative_extensions.dialects.postgresql import Grant
from sqlalchemy_declarative_extensions.grant.compare import (
    GrantPrivilegesOp,
    compare_grants,
)

pg = create_postgres_fixture(scope="function", engine_kwargs={"echo": True})

roles = Roles().are("app")


@pytest.mark.grant
@pytest.mark.parametrize(
    ("setup", "grants"),
    [
        pytest.param(
            "CREATE TABLE t (id int); CREATE MATERIALIZED VIEW mv AS SELECT id FROM t",
            Grants().are(Grant.new("select", to="app").on_tables("mv")),
            id="materialized_view",
        ),
        pytest.param(
            "CREATE TABLE p (id int) PARTITION BY RANGE (id)",
            Grants().are(Grant.new("select", to="app").on_tables("p")),
            id="partitioned_table",
        ),
        pytest.param(
            "SELECT 1",
            Grants().are(Grant.new("create", to="app").on_schemas("public")),
            id="public_schema",
        ),
        pytest.param(
            "CREATE TABLE t (id int)",
            Grants().are(Grant.new("select", to="public").on_tables("t")),
            id="public_role",
        ),
    ],
)
def test_grant_is_applied_once(pg, setup: str, grants: Grants):
    with pg.connect() as conn:
        conn.execute(text("CREATE ROLE app"))
        conn.execute(text(setup))

        diff = compare_grants(conn, grants, roles)
        for op in diff:
            conn.execute(op.to_sql())

        assert [type(op) for op in diff] == [GrantPrivilegesOp]
        assert compare_grants(conn, grants, roles) == []
