import enum

import pytest

from sqlalchemy_declarative_extensions.dialects import mysql, postgresql, snowflake
from sqlalchemy_declarative_extensions.dialects.from_string import FromStrings


def test_from_string_accepts_the_sql_keyword_in_either_case():
    assert postgresql.FunctionVolatility.from_string("STABLE") is (
        postgresql.FunctionVolatility.stable
    )
    assert postgresql.FunctionVolatility.from_string("stable") is (
        postgresql.FunctionVolatility.stable
    )


def test_from_string_accepts_the_member_name():
    """Members whose value contains a space are only reachable by name."""
    assert mysql.FunctionDataAccess.from_string("no_sql") is (
        mysql.FunctionDataAccess.no_sql
    )
    assert postgresql.TriggerTimes.from_string("instead_of") is (
        postgresql.TriggerTimes.instead_of
    )

    # The value spelling still works, and still wins.
    assert mysql.FunctionDataAccess.from_string("no sql") is (
        mysql.FunctionDataAccess.no_sql
    )


def test_from_string_passes_members_through():
    assert postgresql.FunctionSecurity.from_string(
        postgresql.FunctionSecurity.definer
    ) is (postgresql.FunctionSecurity.definer)


def test_from_string_rejects_unknown_strings():
    with pytest.raises(ValueError):
        postgresql.FunctionVolatility.from_string("perhaps")


@pytest.mark.parametrize("module", [postgresql, mysql, snowflake])
def test_every_dialect_enum_is_a_fromstrings(module):
    """Guard against a future enum being added without string coercion."""
    for name in module.__all__:
        obj = getattr(module, name)
        if isinstance(obj, type) and issubclass(obj, enum.Enum):
            assert issubclass(
                obj, FromStrings
            ), f"{module.__name__}.{name} should subclass FromStrings"


def test_postgresql_function_coerces_strings():
    function = postgresql.Function(
        "f",
        "SELECT 1;",
        returns="INTEGER",
        volatility="stable",
        parallel="safe",
        security="definer",
    )

    assert function.volatility is postgresql.FunctionVolatility.stable
    assert function.parallel is postgresql.FunctionParallel.safe
    assert function.security is postgresql.FunctionSecurity.definer

    assert function == postgresql.Function(
        "f",
        "SELECT 1;",
        returns="INTEGER",
        volatility=postgresql.FunctionVolatility.stable,
        parallel=postgresql.FunctionParallel.safe,
        security=postgresql.FunctionSecurity.definer,
    )

    (create,) = function.normalize().to_sql_create()
    assert "SECURITY DEFINER" in create
    assert "STABLE" in create
    assert "PARALLEL SAFE" in create


def test_postgresql_function_with_builders_accept_strings():
    function = postgresql.Function("f", "SELECT 1;", returns="INTEGER")

    assert function.with_volatility("immutable").volatility is (
        postgresql.FunctionVolatility.immutable
    )
    assert function.with_parallel("restricted").parallel is (
        postgresql.FunctionParallel.restricted
    )
    assert function.with_security("definer").security is (
        postgresql.FunctionSecurity.definer
    )


def test_postgresql_procedure_coerces_strings():
    procedure = postgresql.Procedure("p", "SELECT 1;", security="definer")

    assert procedure.security is postgresql.ProcedureSecurity.definer
    assert "SECURITY DEFINER" in procedure.to_sql_create()[0]


def test_postgresql_trigger_coerces_strings_on_direct_construction():
    """Direct construction never coerced; only the before/after classmethods did."""
    trigger = postgresql.Trigger(
        name="t",
        time="before",
        events=["insert", "update"],
        for_each="row",
        on="foo",
        execute="bar",
    )

    assert trigger.time is postgresql.TriggerTimes.before
    assert trigger.events == [
        postgresql.TriggerEvents.insert,
        postgresql.TriggerEvents.update,
    ]
    assert trigger.for_each is postgresql.TriggerForEach.row

    create = trigger.to_sql_create()
    assert "BEFORE INSERT OR UPDATE" in create
    assert "FOR EACH ROW" in create


def test_mysql_function_coerces_strings():
    function = mysql.Function(
        "f",
        "RETURN 1;",
        returns="INTEGER",
        data_access="no_sql",
        security="invoker",
    )

    assert function.data_access is mysql.FunctionDataAccess.no_sql
    assert function.security is mysql.FunctionSecurity.invoker

    (create,) = function.to_sql_create()
    assert "NO SQL" in create
    assert "SQL SECURITY INVOKER" in create

    # The SQL keyword spelling reaches the same member.
    keyword = mysql.Function("f", "RETURN 1;", returns="INTEGER", data_access="NO SQL")
    assert keyword.data_access is mysql.FunctionDataAccess.no_sql


def test_mysql_procedure_coerces_strings():
    procedure = mysql.Procedure("p", "SELECT 1;", security="invoker")

    assert procedure.security is mysql.ProcedureSecurity.invoker
    assert "SQL SECURITY INVOKER" in procedure.to_sql_create()[0]


def test_mysql_trigger_coerces_strings():
    trigger = mysql.Trigger(
        name="t", time="after", event="delete", on="foo", execute="bar"
    )

    assert trigger.time is mysql.TriggerTimes.after
    assert trigger.event is mysql.TriggerEvents.delete

    ordered = trigger.follows("other")
    assert ordered.order is not None
    assert ordered.order.order is mysql.TriggerOrders.follows

    assert "AFTER DELETE" in ordered.to_sql_create()


def test_snowflake_role_coerces_strings():
    role = snowflake.Role("r", default_secondary_roles=["all"])

    assert role.default_secondary_roles == [snowflake.SecondaryRoles.all]
    assert role == snowflake.Role(
        "r", default_secondary_roles=[snowflake.SecondaryRoles.all]
    )


def test_coercion_survives_dataclass_replace():
    """`normalize` and every `with_*` builder re-run `__post_init__`."""
    function = postgresql.Function(
        "f", "SELECT 1;", returns="INTEGER", volatility="stable"
    ).normalize()

    assert function.volatility is postgresql.FunctionVolatility.stable


def test_volatility_and_parallel_values_survive_the_lowercase_rename():
    """The rename moved member names only; values are untouched."""
    assert postgresql.FunctionVolatility("VOLATILE") is (
        postgresql.FunctionVolatility.volatile
    )
    assert postgresql.FunctionVolatility("STABLE") is (
        postgresql.FunctionVolatility.stable
    )
    assert postgresql.FunctionParallel("SAFE") is postgresql.FunctionParallel.safe

    assert postgresql.FunctionVolatility.from_string("stable") is (
        postgresql.FunctionVolatility.stable
    )
    assert postgresql.FunctionParallel.from_string("safe") is (
        postgresql.FunctionParallel.safe
    )


@pytest.mark.parametrize(
    ("enum_cls", "old_name"),
    [
        (postgresql.FunctionVolatility, "VOLATILE"),
        (postgresql.FunctionVolatility, "STABLE"),
        (postgresql.FunctionVolatility, "IMMUTABLE"),
        (postgresql.FunctionParallel, "UNSAFE"),
        (postgresql.FunctionParallel, "RESTRICTED"),
        (postgresql.FunctionParallel, "SAFE"),
    ],
)
def test_old_uppercase_member_names_alias_the_lowercase_members(enum_cls, old_name):
    assert getattr(enum_cls, old_name) is getattr(enum_cls, old_name.lower())
    assert old_name not in [member.name for member in enum_cls]
