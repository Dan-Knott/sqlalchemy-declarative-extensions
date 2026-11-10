from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Generator, Iterable, Sequence

from sqlalchemy import MetaData
from typing_extensions import Self

from sqlalchemy_declarative_extensions.dialects import postgresql
from sqlalchemy_declarative_extensions.role import generic


@dataclass
class Roles:
    roles: Sequence[postgresql.Role | generic.Role] = field(default_factory=list)
    ignore_unspecified: bool = False
    ignore_roles: list[str] = field(default_factory=list)

    @classmethod
    def coerce_from_unknown(
        cls,
        unknown: None | Iterable[postgresql.Role | generic.Role | str] | Roles,
    ) -> Roles | None:
        if isinstance(unknown, Roles):
            return unknown

        if isinstance(unknown, Iterable):
            return Roles().are(*unknown)

        return None

    @classmethod
    def extract(cls, metadata: MetaData | list[MetaData | None] | None) -> Self | None:
        """Extract the declared roles, including `Role` objects that grants are given.

        When no `Roles` are declared, roles from grants are collected into a
        `Roles(ignore_unspecified=True)`, so other existing roles are left alone.
        """
        if not isinstance(metadata, Sequence):
            metadata = [metadata]

        declared = cls._extract_declared(metadata)
        grant_roles = [
            statement.grant.role
            for m in metadata
            if m and m.info.get("grants")
            for statement in m.info["grants"]
            if isinstance(statement.grant.role, generic.Role)
        ]
        if not grant_roles:
            return declared

        if declared is None:
            result = cls(ignore_unspecified=True)
        else:
            result = replace(declared, roles=list(declared.roles))

        for role in grant_roles:
            result.append(role)
        return result

    @classmethod
    def _extract_declared(cls, metadata: Sequence[MetaData | None]) -> Self | None:
        instances: list[Self] = [
            m.info["roles"] for m in metadata if m and m.info.get("roles")
        ]

        instance_count = len(instances)
        if instance_count == 0:
            return None

        if instance_count == 1:
            return instances[0]

        if not all(
            x.ignore_unspecified == instances[0].ignore_unspecified for x in instances
        ):
            raise ValueError(
                "All combined `Roles` instances must agree on the set of settings: ignore_unspecified"
            )

        roles = tuple(s for instance in instances for s in instance.roles)
        ignore_roles = [s for instance in instances for s in instance.ignore_roles]

        ignore_unspecified = instances[0].ignore_unspecified
        return cls(
            roles=roles,
            ignore_unspecified=ignore_unspecified,
            ignore_roles=ignore_roles,
        )

    def append(self, role: postgresql.Role | generic.Role):
        """Add the role, and any `Role` it is in, unless an equivalent one is present.

        A role given only by name (e.g. `Roles().are("app")`) is equivalent to any role
        of that name, and is replaced by it. Raises a `ValueError` if a role of the
        same name is otherwise defined differently.
        """
        role = generic.Role.coerce_from_unknown(role)
        for in_role in role.in_roles or []:
            if isinstance(in_role, generic.Role):
                self.append(in_role)

        existing = [r for r in self.roles if r.name == role.name]
        if not existing:
            self.roles = [*self.roles, role]
            return

        (existing_role,) = existing
        if existing_role.normalize() == role.normalize() or _is_bare(role):
            return

        if not _is_bare(existing_role):
            raise ValueError(
                f"Role '{role.name}' is declared more than once with differing options."
            )

        self.roles = [role if r is existing_role else r for r in self.roles]

    def __iter__(self) -> Generator[postgresql.Role | generic.Role, None, None]:
        yield from self.roles

    def are(self, *roles: postgresql.Role | generic.Role | str):
        return replace(
            self,
            roles=[generic.Role.coerce_from_unknown(role) for role in roles],
        )


def _is_bare(role: generic.Role) -> bool:
    return role.normalize() == generic.Role(role.name).normalize()
