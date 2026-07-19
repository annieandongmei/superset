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

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import Mock

from superset.utils import json
from superset.utils.dashboard_filter_scopes_converter import (
    convert_filter_scopes,
    copy_filter_scopes,
)


def _filter_box(slice_id: int, params: dict[str, Any]) -> Mock:
    """Build a lightweight stand-in for a ``Slice`` filter-box."""
    filter_box = Mock()
    filter_box.id = slice_id
    filter_box.params = json.dumps(params)
    return filter_box


def test_convert_filter_scopes_time_filters() -> None:
    """The three time pseudo-columns are added when their flags are set."""
    filter_box = _filter_box(
        1,
        {
            "date_filter": True,
            "show_sqla_time_column": True,
            "show_sqla_time_granularity": True,
        },
    )

    result = convert_filter_scopes({}, [filter_box])

    assert set(result[1]) == {"__time_range", "__time_col", "__time_grain"}
    for scope in result[1].values():
        assert scope == {"scope": ["ROOT_ID"], "immune": []}


def test_convert_filter_scopes_filter_configs_columns() -> None:
    """Each ``filter_configs`` column becomes a scoped filter field."""
    filter_box = _filter_box(
        7,
        {"filter_configs": [{"column": "country"}, {"column": "gender"}]},
    )

    result = convert_filter_scopes({}, [filter_box])

    assert set(result[7]) == {"country", "gender"}


def test_convert_filter_scopes_immune_by_id_and_column() -> None:
    """Immune slices come from both the global list and per-column mapping."""
    json_metadata = {
        "filter_immune_slices": [10, 20],
        "filter_immune_slice_fields": {"30": ["country"]},
    }
    filter_box = _filter_box(7, {"filter_configs": [{"column": "country"}]})

    result = convert_filter_scopes(json_metadata, [filter_box])

    assert sorted(result[7]["country"]["immune"]) == [10, 20, 30]


def test_convert_filter_scopes_invalid_field_is_skipped(caplog) -> None:
    """A non-string filter field is logged and excluded from the scopes."""
    filter_box = _filter_box(3, {"filter_configs": [{"column": 12345}]})

    with caplog.at_level(logging.INFO):
        result = convert_filter_scopes({}, [filter_box])

    assert result == {}
    assert any("invalid field" in record.getMessage() for record in caplog.records)


def test_convert_filter_scopes_empty_params_produces_no_entry() -> None:
    """A filter box without any relevant params yields no scope entry."""
    filter_box = _filter_box(9, {})

    result = convert_filter_scopes({}, [filter_box])

    assert result == {}


def test_convert_filter_scopes_handles_null_params() -> None:
    """A ``None`` params value falls back to an empty configuration."""
    filter_box = Mock()
    filter_box.id = 4
    filter_box.params = None

    result = convert_filter_scopes({}, [filter_box])

    assert result == {}


def test_copy_filter_scopes_remaps_ids_and_immune() -> None:
    """Filter and immune ids are translated using the id mapping."""
    old_to_new = {1: 100, 2: 200, 3: 300}
    old_filter_scopes: dict[int, dict[str, dict[str, Any]]] = {
        1: {"country": {"scope": ["ROOT_ID"], "immune": [2, 3]}},
    }

    result = copy_filter_scopes(old_to_new, old_filter_scopes)

    assert result == {
        "100": {"country": {"scope": ["ROOT_ID"], "immune": [200, 300]}},
    }


def test_copy_filter_scopes_drops_unmapped_filter_and_immune() -> None:
    """Filters/immune ids missing from the mapping are dropped."""
    old_to_new = {1: 100}
    old_filter_scopes: dict[int, dict[str, dict[str, Any]]] = {
        1: {"country": {"scope": ["ROOT_ID"], "immune": [2, 3]}},
        2: {"gender": {"scope": ["ROOT_ID"], "immune": []}},
    }

    result = copy_filter_scopes(old_to_new, old_filter_scopes)

    assert result == {"100": {"country": {"scope": ["ROOT_ID"], "immune": []}}}
