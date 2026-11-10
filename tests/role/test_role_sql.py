from unittest.mock import Mock

from sqlalchemy_declarative_extensions.dialects.postgresql import Role


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
