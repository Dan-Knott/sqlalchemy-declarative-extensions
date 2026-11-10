from sqlalchemy import Column, types

from sqlalchemy_declarative_extensions import (
    Grants,
    declarative_database,
    view,
)
from sqlalchemy_declarative_extensions.dialects.postgresql import (
    Function,
    Grant,
    GrantTypes,
    Role,
)
from sqlalchemy_declarative_extensions.sqlalchemy import declarative_base

_Base = declarative_base()

reader = Role("reader")


@declarative_database
class Base(_Base):  # type: ignore
    __abstract__ = True

    functions = [Function("one", "SELECT 1", returns="integer")]
    grants = Grants().are(
        Grant.new("execute", to=reader).on_objects(
            "one", object_type=GrantTypes.function
        )
    )


class Foo(Base):
    __tablename__ = "foo"
    __table_args__ = (Grant.new("select", "insert", to=reader),)

    id = Column(types.Integer(), primary_key=True)


@view(Base)
class Bar:
    __tablename__ = "bar"
    __table_args__ = (Grant.new("select", to=reader),)
    __view__ = "SELECT id FROM foo"
