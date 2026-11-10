from sqlalchemy import Column, types

from sqlalchemy_declarative_extensions import (
    Grants,
    Roles,
    declarative_database,
    view,
)
from sqlalchemy_declarative_extensions.dialects.postgresql import Grant, Role
from sqlalchemy_declarative_extensions.sqlalchemy import declarative_base

_Base = declarative_base()

reader = Role("reader")


@declarative_database
class Base(_Base):  # type: ignore
    __abstract__ = True

    roles = Roles(ignore_unspecified=True).are(reader)
    grants = Grants().are(
        Grant.new("select", "insert", to=reader).on_tables("foo"),
        Grant.new("select", to=reader).on_tables("bar"),
    )


class Foo(Base):
    __tablename__ = "foo"

    id = Column(types.Integer(), primary_key=True)


@view(Base)
class Bar:
    __tablename__ = "bar"
    __view__ = "SELECT id FROM foo"
