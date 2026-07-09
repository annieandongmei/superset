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

from superset.models.slice import Slice
from superset.utils import json
from superset.utils.dashboard_filter_scopes_converter import (
    convert_filter_scopes,
    copy_filter_scopes,
)


def make_filter_box(slice_id: int, params: dict[str, Any]) -> Slice:
    """Build an in-memory filter-box ``Slice`` (not persisted to the session)."""
    return Slice(id=slice_id, params=json.dumps(params))


def test_convert_filter_scopes_time_filters() -> None:
    filter_box = make_filter_box(
        1,
        {
            "date_filter": True,
            "show_sqla_time_column": True,
            "show_sqla_time_granularity": True,
        },
    )
    result = convert_filter_scopes({}, [filter_box])
    assert set(result[1]) == {"__time_range", "__time_col", "__time_grain"}
    for field in result[1].values():
        assert field == {"scope": ["ROOT_ID"], "immune": []}


def test_convert_filter_scopes_filter_configs() -> None:
    filter_box = make_filter_box(
        7,
        {"filter_configs": [{"column": "country"}, {"column": "gender"}]},
    )
    result = convert_filter_scopes({}, [filter_box])
    assert set(result[7]) == {"country", "gender"}
    assert result[7]["country"]["scope"] == ["ROOT_ID"]


def test_convert_filter_scopes_immune_by_id_and_column() -> None:
    filter_box = make_filter_box(1, {"filter_configs": [{"column": "country"}]})
    json_metadata = {
        "filter_immune_slices": [2],
        "filter_immune_slice_fields": {"3": ["country"]},
    }
    result = convert_filter_scopes(json_metadata, [filter_box])
    assert set(result[1]["country"]["immune"]) == {2, 3}


def test_convert_filter_scopes_invalid_field_is_skipped() -> None:
    # ``column`` is not a string, so ``add_filter_scope`` logs and skips it.
    filter_box = make_filter_box(1, {"filter_configs": [{"column": 123}]})
    result = convert_filter_scopes({}, [filter_box])
    assert result == {}


def test_convert_filter_scopes_no_params() -> None:
    filter_box = make_filter_box(1, {})
    filter_box.params = None
    result = convert_filter_scopes({}, [filter_box])
    assert result == {}


def test_copy_filter_scopes_remaps_ids() -> None:
    old_filter_scopes = {
        1: {"country": {"scope": ["ROOT_ID"], "immune": [2, 3]}},
    }
    result = copy_filter_scopes(
        old_to_new_slc_id_dict={1: 10, 2: 20},
        old_filter_scopes=old_filter_scopes,
    )
    assert "10" in result
    # ``3`` is not in the mapping and is therefore dropped from immune.
    assert result["10"]["country"]["immune"] == [20]


def test_copy_filter_scopes_drops_unmapped_filter() -> None:
    old_filter_scopes = {
        99: {"country": {"scope": ["ROOT_ID"], "immune": []}},
    }
    result = copy_filter_scopes(
        old_to_new_slc_id_dict={1: 10},
        old_filter_scopes=old_filter_scopes,
    )
    assert result == {}
