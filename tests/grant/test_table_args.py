from sqlalchemy import Column, types

from sqlalchemy_declarative_extensions import Grants, declare_database
from sqlalchemy_declarative_extensions.dialects.postgresql import Grant
from sqlalchemy_declarative_extensions.sqlalchemy import declarative_base


def create_base(grants=None):
    declarative = declarative_base()

    class Base(declarative):  # type: ignore
        __abstract__ = True

    declare_database(Base.metadata, grants=grants)
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
