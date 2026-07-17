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

import pytest
from sqlalchemy import types as sqla_types
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm.session import Session

from superset.commands.database.exceptions import DatabaseInvalidError
from superset.databases.utils import (
    get_col_type,
    get_foreign_keys_metadata,
    get_indexes_metadata,
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


def test_make_url_safe_invalid_string() -> None:
    """
    Test that invalid URL strings raise DatabaseInvalidError
    """
    with pytest.raises(DatabaseInvalidError):
        make_url_safe("not a valid url")


def test_get_col_type_normal() -> None:
    """
    Test get_col_type with normal column type
    """
    col = {"type": sqla_types.Integer()}
    result = get_col_type(col)
    assert result == "INTEGER"


def test_get_col_type_with_params() -> None:
    """
    Test get_col_type with type parameters
    """
    col = {"type": sqla_types.VARCHAR(255)}
    result = get_col_type(col)
    assert result == "VARCHAR(255)"


def test_get_col_type_json_type() -> None:
    """
    Test get_col_type with JSON type (which has __str__ bug)
    """
    col = {"type": sqla_types.JSON()}
    result = get_col_type(col)
    assert result == "JSON"


def test_get_foreign_keys_metadata() -> None:
    """
    Test get_foreign_keys_metadata transforms constrained_columns to column_names
    """
    database = type(
        "MockDB",
        (),
        {
            "get_foreign_keys": lambda self, table: [
                {"constrained_columns": ["col1", "col2"], "name": "fk1"}
            ]
        },
    )()
    table = Table(schema="public", table="test")

    result = get_foreign_keys_metadata(database, table)

    assert len(result) == 1
    assert result[0]["column_names"] == ["col1", "col2"]
    assert result[0]["type"] == "fk"
    assert "constrained_columns" not in result[0]


def test_get_indexes_metadata() -> None:
    """
    Test get_indexes_metadata adds type field
    """
    database = type(
        "MockDB",
        (),
        {
            "get_indexes": lambda self, table: [
                {"name": "idx1", "column_names": ["col1"]}
            ]
        },
    )()
    table = Table(schema="public", table="test")

    result = get_indexes_metadata(database, table)

    assert len(result) == 1
    assert result[0]["type"] == "index"
    assert result[0]["name"] == "idx1"
