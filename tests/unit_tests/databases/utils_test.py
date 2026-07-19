# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm.session import Session

from superset.commands.database.exceptions import DatabaseInvalidError
from superset.databases.utils import (
    get_col_type,
    get_foreign_keys_metadata,
    get_indexes_metadata,
    get_table_metadata,
    make_url_safe,
)
from superset.sql.parse import Table


def test_make_url_safe_string(session: Session) -> None:
    """
    Test converting a string to a safe uri
    """
    uri_string = "postgresql+psycopg2://superset:***@127.0.0.1:5432/superset"
    uri_safe = make_url_safe(uri_string)
    assert str(uri_safe) == uri_string
    assert uri_safe == make_url(uri_string)


def test_make_url_safe_url(session: Session) -> None:
    """
    Test converting a url to a safe uri
    """
    uri = make_url("postgresql+psycopg2://superset:***@127.0.0.1:5432/superset")
    uri_safe = make_url_safe(uri)
    assert uri_safe == uri


def test_make_url_safe_invalid_raises_database_invalid_error() -> None:
    """
    An unparseable URI is converted into a log-safe DatabaseInvalidError.
    """
    with pytest.raises(DatabaseInvalidError):
        make_url_safe("not a valid uri ://:::")


def test_get_foreign_keys_metadata_renames_and_tags() -> None:
    """
    ``constrained_columns`` is renamed to ``column_names`` and typed as ``fk``.
    """
    database = MagicMock()
    database.get_foreign_keys.return_value = [
        {"name": "fk_a", "constrained_columns": ["a_id"]},
    ]

    result = get_foreign_keys_metadata(database, Table("t"))

    assert result == [{"name": "fk_a", "column_names": ["a_id"], "type": "fk"}]
    database.get_foreign_keys.assert_called_once()


def test_get_indexes_metadata_tags_type() -> None:
    """
    Each index is tagged with ``type == "index"``.
    """
    database = MagicMock()
    database.get_indexes.return_value = [{"name": "idx", "column_names": ["a"]}]

    result = get_indexes_metadata(database, Table("t"))

    assert result == [{"name": "idx", "column_names": ["a"], "type": "index"}]


def test_get_col_type_uses_str() -> None:
    """
    The normal path stringifies the column type.
    """
    assert get_col_type({"type": "VARCHAR"}) == "VARCHAR"


def test_get_col_type_falls_back_to_class_name() -> None:
    """
    When ``str(type)`` raises, the class name is used instead.
    """

    class ExplodingType:
        def __str__(self) -> str:
            raise ValueError("boom")

    assert get_col_type({"type": ExplodingType()}) == "ExplodingType"


def _build_database_mock() -> MagicMock:
    database = MagicMock()
    database.get_columns.return_value = [
        {"column_name": "id", "type": "INTEGER", "comment": None},
        {"column_name": "name", "type": "VARCHAR(255)", "comment": "the name"},
    ]
    database.get_pk_constraint.return_value = {"constrained_columns": ["id"]}
    database.get_foreign_keys.return_value = [
        {"name": "fk_name", "constrained_columns": ["name"]},
    ]
    database.get_indexes.return_value = [{"name": "idx_name", "column_names": ["name"]}]
    database.get_table_comment.return_value = "a table"
    database.select_star.return_value = "SELECT * FROM t"
    return database


def test_get_table_metadata_full_payload() -> None:
    """
    ``get_table_metadata`` assembles columns, keys and select star.
    """
    database = _build_database_mock()

    payload = get_table_metadata(database, Table("mytable"))

    assert payload["name"] == "mytable"
    assert payload["comment"] == "a table"
    assert payload["selectStar"] == "SELECT * FROM t"
    assert payload["primaryKey"] == {"column_names": ["id"], "type": "pk"}

    columns_by_name: dict[str, Any] = {col["name"]: col for col in payload["columns"]}
    # A parametrized type is split for the short ``type`` but kept in ``longType``.
    assert columns_by_name["name"]["type"] == "VARCHAR"
    assert columns_by_name["name"]["longType"] == "VARCHAR(255)"
    assert columns_by_name["id"]["type"] == "INTEGER"
    # The ``id`` column is linked to the primary key.
    assert any(key["type"] == "pk" for key in columns_by_name["id"]["keys"])
    # The ``name`` column is linked to both the foreign key and index.
    name_key_types = {key["type"] for key in columns_by_name["name"]["keys"]}
    assert name_key_types == {"fk", "index"}


def test_get_table_metadata_without_primary_key() -> None:
    """
    A missing primary key constraint is handled gracefully.
    """
    database = _build_database_mock()
    database.get_pk_constraint.return_value = {}

    payload = get_table_metadata(database, Table("mytable"))

    assert payload["primaryKey"] == {}
    columns_by_name: dict[str, Any] = {col["name"]: col for col in payload["columns"]}
    assert all(key["type"] != "pk" for key in columns_by_name["id"]["keys"])
