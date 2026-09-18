# Functions

```python
from sqlalchemy.orm import declarative_base
from sqlalchemy_declarative_extensions import declarative_database, Functions

# Import dialect-specific Function for full feature support
from sqlalchemy_declarative_extensions.dialects.postgresql import Function, FunctionReturn
# from sqlalchemy_declarative_extensions.dialects.mysql import Function

_Base = declarative_base()

@declarative_database
class Base(_Base):
    __abstract__ = True

    functions = Functions().are(
        Function("gimme", "SELECT 1;", returns="INTEGER"),
        Function(
            "fancy_trigger",
            """
            BEGIN
            INSERT INTO foo (id) select NEW.id + 1;
            RETURN NULL;
            END
            """,
            language="plpgsql",
            returns="trigger",
        ),
        Function(
            "gimme_rows",
            '''
            SELECT id, name
            FROM dem_rowz
            WHERE group_id = _group_id;
            ''',
            language="sql",
            parameters=["_group_id int"],
            returns=FunctionReturn(table=[("id", "int"), ("name", "text")]),
            volatility='stable', # PostgreSQL specific characteristic
        )

        # Example MySQL function
        # Function(
        #    "gimme_concat",
        #    "RETURN CONCAT(label, ': ', CAST(val AS CHAR));",
        #    parameters=["val INT", "label VARCHAR(50)"],
        #    returns="VARCHAR(100)",
        #    deterministic=True, # MySQL specific
        #    data_access='NO SQL', # MySQL specific
        #    security='INVOKER', # MySQL specific
        # ),
    )
```

```{note}
Every enum-valued option accepts a plain string, so you never need to import the enum type.
Both the SQL keyword and the enum's member name are accepted, case-insensitively: `volatility='stable'`,
`parallel='safe'`, `security='definer'`, and (MySQL) `data_access='NO SQL'` or `data_access='no_sql'`.
```

```{note}
Functions options are wildly different across dialects. As such, you should likely always use
the dialect-specific `Function` object (e.g., `sqlalchemy_declarative_extensions.dialects.postgresql.Function`
or `sqlalchemy_declarative_extensions.dialects.mysql.Function`) to access all available features.
The base `Function` provides only the most common subset of options.
```

```{note}
Function comparison parses and compares function parameters (including name and type) as well as
dialect-specific characteristics:

*   **PostgreSQL:** `LANGUAGE`, `VOLATILITY`, `SECURITY`, `PARALLEL`, `STRICT`, `LEAKPROOF`, and
    `RETURNS TABLE(...)` syntax.
*   **MySQL:** `DETERMINISTIC`, `DATA ACCESS`, `SECURITY`.

Comparison normalizes types (e.g., mapping `integer` to `int4` in PostgreSQL) to ensure accurate
idempotency checks during Alembic autogeneration.
```

```{eval-rst}
.. autoapimodule:: sqlalchemy_declarative_extensions.function.base
   :members: Functions, Function, register_function, Procedure
```

Note, there also exist dialect-specific variants which you must use in order to make use of
any dialect-specific options. The dialect-specific `Function`, `Procedure`, and their supporting
types are documented alongside their dialect, under [Postgresql](dialects/postgresql.md) and
[MySQL](dialects/mysql.md).
