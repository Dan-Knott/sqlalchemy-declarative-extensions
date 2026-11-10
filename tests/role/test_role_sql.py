from unittest.mock import Mock

from sqlalchemy_declarative_extensions import Role as GenericRole
from sqlalchemy_declarative_extensions.dialects.postgresql import Role


def test_generic_create_in_role():
    role = GenericRole("app", in_roles=["read"])

    assert role.to_sql_create() == ['CREATE ROLE "app" IN ROLE "read";']


def test_update_with_use_role():
    role = Role("app", login=False, use_role="admin")

    sql = role.to_sql_update(Role("app", login=True))

    assert sql == [
        'SET ROLE "admin";',
        'ALTER ROLE "app" WITH LOGIN;',
        "RESET ROLE;",
    ]


def test_from_unknown_role_keeps_use_role():
    role = Role.from_unknown_role(GenericRole("app", use_role="admin", external=True))

    assert role.use_role == "admin"
    assert role.external is True


def test_use_role_is_not_compared():
    assert Role("app", use_role="admin") == Role("app")


def test_from_pg_role_reads_inherit():
    row = Mock(
        rolname="app",
        rolsuper=False,
        rolinherit=False,
        rolcreatedb=False,
        rolcreaterole=False,
        rolcanlogin=False,
        rolreplication=False,
        rolconnlimit=-1,
        rolbypassrls=False,
        rolvaliduntil=None,
        memberof=[],
    )

    assert Role.from_pg_role(row).inherit is False
