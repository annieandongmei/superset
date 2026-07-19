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

"""Tests for MCP schema discovery helpers."""

from superset.mcp_service.common.schema_discovery import (
    _audit_extra_columns,
    CHART_EXTRA_COLUMNS,
    ColumnMetadata,
    DASHBOARD_EXTRA_COLUMNS,
    DATABASE_EXTRA_COLUMNS,
    DATASET_EXTRA_COLUMNS,
    get_columns_from_model,
)
from superset.models.slice import Slice


def test_get_columns_from_model_excludes_matching_extra_columns():
    columns = get_columns_from_model(
        Slice,
        default_columns=["id"],
        extra_columns={
            "editors": ColumnMetadata(**CHART_EXTRA_COLUMNS["editors"].model_dump()),
            "url": ColumnMetadata(**CHART_EXTRA_COLUMNS["url"].model_dump()),
        },
        exclude_columns={"editors"},
    )

    column_names = {column.name for column in columns}

    assert "id" in column_names
    assert "url" in column_names
    assert "editors" not in column_names


def test_audit_extra_columns_shared_across_models():
    audit = _audit_extra_columns()
    expected_names = {
        "changed_by",
        "changed_by_name",
        "changed_on_humanized",
        "created_by",
        "created_by_name",
        "created_on_humanized",
    }
    assert set(audit) == expected_names

    for mapping in (
        CHART_EXTRA_COLUMNS,
        DATASET_EXTRA_COLUMNS,
        DASHBOARD_EXTRA_COLUMNS,
        DATABASE_EXTRA_COLUMNS,
    ):
        for name, meta in audit.items():
            assert mapping[name].model_dump() == meta.model_dump()


def test_audit_extra_columns_returns_fresh_instances():
    first = _audit_extra_columns()
    second = _audit_extra_columns()
    assert first is not second
    assert first["changed_by"] is not second["changed_by"]
