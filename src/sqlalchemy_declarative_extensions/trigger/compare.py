from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from typing import Sequence, Union

from sqlalchemy.engine import Connection

from sqlalchemy_declarative_extensions.dialects import get_triggers
from sqlalchemy_declarative_extensions.op import ExecuteOp
from sqlalchemy_declarative_extensions.trigger.base import Trigger, Triggers


@dataclass
class CreateTriggerOp(ExecuteOp):
    trigger: Trigger

    def reverse(self):
        return DropTriggerOp(self.trigger)

    def to_sql(self, connection: Connection | None = None) -> list[str]:
        return [self.trigger.to_sql_create()]


@dataclass
class UpdateTriggerOp(ExecuteOp):
    from_trigger: Trigger
    trigger: Trigger

    def reverse(self):
        return UpdateTriggerOp(from_trigger=self.trigger, trigger=self.from_trigger)

    def to_sql(self, connection: Connection | None = None) -> list[str]:
        return self.trigger.to_sql_update(connection)


@dataclass
class DropTriggerOp(ExecuteOp):
    trigger: Trigger

    def reverse(self):
        return CreateTriggerOp(self.trigger)

    def to_sql(self, connection: Connection | None = None) -> list[str]:
        return [self.trigger.to_sql_drop()]


Operation = Union[CreateTriggerOp, UpdateTriggerOp, DropTriggerOp]


def compare_triggers(connection: Connection, triggers: Triggers) -> list[Operation]:
    result: list[Operation] = []

    triggers_by_name = {r.name: r for r in triggers.triggers}
    expected_trigger_names = set(triggers_by_name)

    raw_existing_triggers = get_triggers(connection)
    existing_triggers = filter_triggers(
        raw_existing_triggers, exclude=triggers.ignore, include=triggers.include
    )

    existing_triggers_by_name = {r.name: r for r in existing_triggers}
    existing_trigger_names = set(existing_triggers_by_name)

    new_trigger_names = expected_trigger_names - existing_trigger_names
    removed_trigger_names = existing_trigger_names - expected_trigger_names

    for trigger in triggers:
        trigger_created = trigger.name in new_trigger_names

        if trigger_created:
            result.append(CreateTriggerOp(trigger))
        else:
            existing_trigger = existing_triggers_by_name[trigger.name]

            if existing_trigger != trigger:
                result.append(UpdateTriggerOp(existing_trigger, trigger))

    if not triggers.ignore_unspecified:
        for removed_trigger in removed_trigger_names:
            trigger = existing_triggers_by_name[removed_trigger]
            result.append(DropTriggerOp(trigger))

    return result


def filter_triggers(
    triggers: Sequence[Trigger], *, exclude: list[str], include: list[str] | None
) -> list[Trigger]:
    return [
        t
        for t in triggers
        if (
            include is None
            or any(fnmatch.fnmatch(t.name, inclusion) for inclusion in include)
        )
        and not any(fnmatch.fnmatch(t.name, exclusion) for exclusion in exclude)
    ]
