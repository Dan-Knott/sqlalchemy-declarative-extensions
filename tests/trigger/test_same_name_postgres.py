from unittest.mock import Mock

from sqlalchemy_declarative_extensions import Triggers
from sqlalchemy_declarative_extensions.dialects.postgresql import Trigger
from sqlalchemy_declarative_extensions.trigger.compare import (
    CreateTriggerOp,
    DropTriggerOp,
    UpdateTriggerOp,
    compare_triggers,
)


def trigger(on: str, event: str = "insert"):
    return Trigger.after(event, on=on, execute="gimme").named("on_change")


def test_same_name_on_different_tables_matches_existing(monkeypatch):
    expected = Triggers().are(trigger("foo"), trigger("bar"))
    monkeypatch.setattr(
        "sqlalchemy_declarative_extensions.trigger.compare.get_triggers",
        Mock(return_value=list(expected)),
    )

    assert compare_triggers(Mock(), expected) == []


def test_same_name_on_different_table_is_created(monkeypatch):
    foo_trigger = trigger("foo")
    bar_trigger = trigger("bar")
    expected = Triggers().are(foo_trigger, bar_trigger)
    monkeypatch.setattr(
        "sqlalchemy_declarative_extensions.trigger.compare.get_triggers",
        Mock(return_value=[foo_trigger]),
    )

    assert compare_triggers(Mock(), expected) == [CreateTriggerOp(bar_trigger)]


def test_same_name_updates_only_trigger_on_matching_table(monkeypatch):
    foo_trigger = trigger("foo")
    old_bar_trigger = trigger("bar")
    new_bar_trigger = trigger("bar", event="update")
    expected = Triggers().are(foo_trigger, new_bar_trigger)
    monkeypatch.setattr(
        "sqlalchemy_declarative_extensions.trigger.compare.get_triggers",
        Mock(return_value=[foo_trigger, old_bar_trigger]),
    )

    assert compare_triggers(Mock(), expected) == [
        UpdateTriggerOp(old_bar_trigger, new_bar_trigger)
    ]


def test_same_name_drops_only_trigger_on_unspecified_table(monkeypatch):
    foo_trigger = trigger("foo")
    bar_trigger = trigger("bar")
    expected = Triggers().are(foo_trigger)
    monkeypatch.setattr(
        "sqlalchemy_declarative_extensions.trigger.compare.get_triggers",
        Mock(return_value=[foo_trigger, bar_trigger]),
    )

    assert compare_triggers(Mock(), expected) == [DropTriggerOp(bar_trigger)]
