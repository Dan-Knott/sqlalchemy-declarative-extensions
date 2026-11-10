from __future__ import annotations

from dataclasses import dataclass
from itertools import groupby
from typing import Container, Union

from sqlalchemy.engine import Connection

from sqlalchemy_declarative_extensions.dialects import (
    get_default_grants,
    get_grants,
    get_objects,
)
from sqlalchemy_declarative_extensions.dialects.postgresql import (
    DefaultGrantStatement,
    GrantStatement,
    GrantTypes,
)
from sqlalchemy_declarative_extensions.dialects.postgresql.grant import PUBLIC
from sqlalchemy_declarative_extensions.grant.base import Grants
from sqlalchemy_declarative_extensions.op import ExecuteOp
from sqlalchemy_declarative_extensions.role.base import Roles


@dataclass
class GrantPrivilegesOp(ExecuteOp):
    grant: DefaultGrantStatement | GrantStatement

    def reverse(self):
        return RevokePrivilegesOp(self.grant)

    def to_sql(self):
        return self.grant.to_sql()


@dataclass
class RevokePrivilegesOp(ExecuteOp):
    grant: DefaultGrantStatement | GrantStatement

    def reverse(self):
        return GrantPrivilegesOp(self.grant)

    def to_sql(self):
        return self.grant.invert().to_sql()


Operation = Union[GrantPrivilegesOp, RevokePrivilegesOp]


def compare_grants(
    connection: Connection,
    grants: Grants,
    roles: Roles | None = None,
    *,
    object_grants: bool = True,
) -> list[Operation]:
    result: list[Operation] = []

    assert connection.engine.url.username
    current_role: str = connection.engine.url.username

    filtered_roles: set[str] | None = None
    if grants.only_defined_roles:
        filtered_roles = {r.name for r in (roles or [])}
        if any(grant.grant.target_role == PUBLIC for grant in grants):
            filtered_roles.add(PUBLIC)

    default_grant_ops = compare_default_grants(connection, grants, roles=filtered_roles)
    result.extend(default_grant_ops)

    has_object_grants = any(isinstance(grant, GrantStatement) for grant in grants)
    if object_grants and (grants.default_grants_imply_grants or has_object_grants):
        grant_ops = compare_object_grants(
            connection, grants, username=current_role, roles=filtered_roles
        )
        result.extend(grant_ops)

    return result


def compare_default_grants(
    connection: Connection,
    grants: Grants,
    roles: Container[str] | None = None,
):
    result: list[Operation] = []

    existing_default_grants = get_default_grants(connection, roles=roles, expanded=True)

    expected_grants = []
    for grant in grants:
        if not isinstance(grant, DefaultGrantStatement):
            continue

        expected_grants.extend(grant.explode())

    missing_grants = set(expected_grants) - set(existing_default_grants)
    extra_grants = set(existing_default_grants) - set(expected_grants)

    if not grants.ignore_unspecified:
        for grant in DefaultGrantStatement.combine(list(extra_grants)):
            result.append(RevokePrivilegesOp(grant))

    for grant in DefaultGrantStatement.combine(list(missing_grants)):
        result.append(GrantPrivilegesOp(grant))

    return result


def compare_object_grants(
    connection: Connection,
    grants: Grants,
    username: str,
    roles: Container[str] | None = None,
):
    result: list[Operation] = []

    expected_grants = {
        sub_g
        for grant in grants
        if isinstance(grant, GrantStatement)
        for sub_g in grant.explode()
    }

    implied_grants = _implied_grants(connection, grants)
    if grants.default_grants_imply_grants:
        expected_grants |= implied_grants

    targets_public_schema = any(
        isinstance(grant, GrantStatement)
        and grant.grant_type == GrantTypes.schema
        and "public" in grant.targets
        for grant in grants
    )
    existing_grants = get_grants(
        connection, roles=roles, expanded=True, public_schema=targets_public_schema
    )

    if grants.ignore_self_grants:
        existing_grants = [
            g for g in existing_grants if g.grant.target_role != username
        ]

    missing_grants = expected_grants - set(existing_grants)
    extra_grants = set(existing_grants) - expected_grants - implied_grants

    if not grants.ignore_unspecified:
        for grant in GrantStatement.combine(list(extra_grants)):
            result.append(RevokePrivilegesOp(grant))

    for grant in GrantStatement.combine(list(missing_grants)):
        result.append(GrantPrivilegesOp(grant))

    return result


def _implied_grants(connection: Connection, grants: Grants) -> set[GrantStatement]:
    default_grants = [g for g in grants if isinstance(g, DefaultGrantStatement)]
    if not default_grants:
        return set()

    existing_objects = get_objects(connection)
    existing_objects_by_schema = {
        s: list(g) for s, g in groupby(existing_objects, lambda r: r[0])
    }

    result: set[GrantStatement] = set()
    for grant in default_grants:
        grant_type = grant.default_grant.grant_type.to_grant_type()

        for schema in grant.default_grant.in_schemas:
            for _, name, relkind in existing_objects_by_schema.get(schema, []):
                object_type = GrantTypes.from_relkind(relkind)
                if object_type != grant_type:
                    continue

                result.update(
                    grant.grant.on_objects(name, object_type=object_type).explode()
                )

    return result
