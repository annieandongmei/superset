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


def test_make_url_safe_invalid_raises() -> None:
    """
    Invalid connection strings should raise a generic ``DatabaseInvalidError``
    rather than leaking the raw (potentially credential-bearing) SQLAlchemy error.
    """
    with pytest.raises(DatabaseInvalidError):
        make_url_safe("this is not a valid uri://")


def test_get_col_type_from_str() -> None:
    assert get_col_type({"type": "VARCHAR(255)"}) == "VARCHAR(255)"


def test_get_col_type_falls_back_to_class_name() -> None:
    class Boom:
        def __str__(self) -> str:
            raise ValueError("cannot stringify")

    assert get_col_type({"type": Boom()}) == "Boom"


def test_get_foreign_keys_metadata() -> None:
    database = MagicMock()
    database.get_foreign_keys.return_value = [
        {"name": "fk_1", "constrained_columns": ["a", "b"]},
    ]
    table = Table("some_table", "some_schema")
    result = get_foreign_keys_metadata(database, table)
    assert result == [{"name": "fk_1", "column_names": ["a", "b"], "type": "fk"}]
    database.get_foreign_keys.assert_called_once_with(table)


def test_get_indexes_metadata() -> None:
    database = MagicMock()
    database.get_indexes.return_value = [{"name": "idx_1", "column_names": ["a"]}]
    table = Table("some_table", "some_schema")
    result = get_indexes_metadata(database, table)
    assert result == [{"name": "idx_1", "column_names": ["a"], "type": "index"}]


def test_get_table_metadata() -> None:
    database = MagicMock()
    database.get_columns.return_value = [
        {"column_name": "id", "type": "INTEGER", "comment": "pk column"},
        {"column_name": "name", "type": "VARCHAR(255)", "comment": None},
    ]
    database.get_pk_constraint.return_value = {"constrained_columns": ["id"]}
    database.get_foreign_keys.return_value = []
    database.get_indexes.return_value = []
    database.get_table_comment.return_value = "a table"
    database.select_star.return_value = "SELECT * FROM some_table"

    table = Table("some_table", "some_schema")
    result = get_table_metadata(database, table)

    assert result["name"] == "some_table"
    assert result["comment"] == "a table"
    assert result["selectStar"] == "SELECT * FROM some_table"
    assert result["primaryKey"] == {"column_names": ["id"], "type": "pk"}

    columns = {col["name"]: col for col in result["columns"]}
    assert columns["id"]["type"] == "INTEGER"
    assert columns["id"]["comment"] == "pk column"
    # The ``id`` column participates in the primary key, so it carries the key.
    assert columns["id"]["keys"] == [{"column_names": ["id"], "type": "pk"}]
    # ``VARCHAR(255)`` is split into a short ``type`` and full ``longType``.
    assert columns["name"]["type"] == "VARCHAR"
    assert columns["name"]["longType"] == "VARCHAR(255)"
    assert columns["name"]["keys"] == []


def test_get_table_metadata_without_primary_key() -> None:
    database = MagicMock()
    database.get_columns.return_value = []
    database.get_pk_constraint.return_value = {}
    database.get_foreign_keys.return_value = []
    database.get_indexes.return_value = []
    database.get_table_comment.return_value = None
    database.select_star.return_value = "SELECT * FROM empty_table"

    table = Table("empty_table", "some_schema")
    result = get_table_metadata(database, table)

    assert result["columns"] == []
    assert result["indexes"] == []
    database.select_star.assert_called_once()
