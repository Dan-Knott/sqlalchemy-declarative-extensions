import pytest
from sqlalchemy import Column, types

from sqlalchemy_declarative_extensions import Grants, Roles, declare_database
from sqlalchemy_declarative_extensions.dialects.postgresql import Grant, Role
from sqlalchemy_declarative_extensions.sqlalchemy import declarative_base


def create_base(roles=None, grants=None):
    declarative = declarative_base()

    class Base(declarative):  # type: ignore
        __abstract__ = True

    declare_database(Base.metadata, roles=roles, grants=grants)
    return Base


def test_grant_targets_the_table():
    base = create_base()

    class Foo(base):
        __tablename__ = "foo"
        __table_args__ = (
            Grant.new("select", to="read"),
            {"schema": "bar"},
        )

        id = Column(types.Integer(), primary_key=True)

    grants = Grants.extract(base.metadata)

    assert grants == Grants().are(Grant.new("select", to="read").on_tables("bar.foo"))


def test_role_object_is_registered():
    base = create_base()
    read = Role("read")
    app = Role("app", in_roles=[read])

    class Foo(base):
        __tablename__ = "foo"
        __table_args__ = (Grant.new("select", to=app),)

        id = Column(types.Integer(), primary_key=True)

    roles = Roles.extract(base.metadata)

    assert roles.ignore_unspecified is True
    assert [r.name for r in roles] == ["read", "app"]


def test_statically_declared_grant_registers_role():
    app = Role("app")
    base = create_base(
        grants=Grants().are(Grant.new("select", to=app).on_tables("foo"))
    )

    roles = Roles.extract(base.metadata)

    assert list(roles) == [app]


def test_declared_role_is_not_duplicated():
    app = Role("app", login=True)
    base = create_base(roles=Roles().are(app))

    class Foo(base):
        __tablename__ = "foo"
        __table_args__ = (Grant.new("select", to=app),)

        id = Column(types.Integer(), primary_key=True)

    roles = Roles.extract(base.metadata)

    assert roles.ignore_unspecified is False
    assert list(roles) == [app]


def test_role_declared_by_name_is_replaced():
    app = Role("app", login=True)
    base = create_base(roles=Roles().are("app"))

    class Foo(base):
        __tablename__ = "foo"
        __table_args__ = (Grant.new("select", to=app),)

        id = Column(types.Integer(), primary_key=True)

    assert list(Roles.extract(base.metadata)) == [app]


def test_conflicting_role_raises():
    base = create_base(roles=Roles().are(Role("app", login=True)))

    class Foo(base):
        __tablename__ = "foo"
        __table_args__ = (Grant.new("select", to=Role("app")),)

        id = Column(types.Integer(), primary_key=True)

    with pytest.raises(ValueError, match="'app'"):
        Roles.extract(base.metadata)


def test_roles_combine_across_metadata():
    declared = create_base(roles=Roles().are("read"))
    inline = create_base()

    class Foo(inline):
        __tablename__ = "foo"
        __table_args__ = (Grant.new("select", to=Role("app")),)

        id = Column(types.Integer(), primary_key=True)

    roles = Roles.extract([declared.metadata, inline.metadata])

    assert [r.name for r in roles] == ["read", "app"]
