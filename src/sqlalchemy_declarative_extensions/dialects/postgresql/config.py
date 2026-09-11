from __future__ import annotations

from typing import Mapping, Sequence

from sqlalchemy_declarative_extensions.sql import quote_name


def config_from_proconfig(proconfig: Sequence[str] | None) -> dict[str, str] | None:
    if not proconfig:
        return None

    config = {}
    for item in proconfig:
        name, _, value = item.partition("=")
        config[name] = value
    return config


def normalize_config(config: Mapping[str, str] | None) -> dict[str, str] | None:
    if not config:
        return None

    return dict(sorted((name.lower(), value) for name, value in config.items()))


def config_to_sql(config: Mapping[str, str]) -> list[str]:
    return [f"SET {quote_name(name)} TO {value}" for name, value in config.items()]
