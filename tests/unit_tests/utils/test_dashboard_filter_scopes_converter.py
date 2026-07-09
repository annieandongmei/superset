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
from superset.utils.dashboard_filter_scopes_converter import (
    convert_filter_scopes,
    copy_filter_scopes,
)


def test_convert_filter_scopes_basic() -> None:
    """Test convert_filter_scopes with basic filter configuration."""
    json_metadata: dict[str, Any] = {
        "filter_immune_slices": [],
        "filter_immune_slice_fields": {},
    }
    
    filter_box = Slice()
    filter_box.id = 1
    filter_box.params = '{"filter_configs": [{"column": "col1"}]}'
    
    result = convert_filter_scopes(json_metadata, [filter_box])
    
    assert 1 in result
    assert "col1" in result[1]
    assert result[1]["col1"]["scope"] == ["ROOT_ID"]
    assert result[1]["col1"]["immune"] == []


def test_convert_filter_scopes_with_immune_slices() -> None:
    """Test convert_filter_scopes with immune slice IDs."""
    json_metadata: dict[str, Any] = {
        "filter_immune_slices": [2, 3],
        "filter_immune_slice_fields": {},
    }
    
    filter_box = Slice()
    filter_box.id = 1
    filter_box.params = '{"filter_configs": [{"column": "col1"}]}'
    
    result = convert_filter_scopes(json_metadata, [filter_box])
    
    assert result[1]["col1"]["immune"] == [2, 3]


def test_convert_filter_scopes_with_immune_fields() -> None:
    """Test convert_filter_scopes with immune field columns."""
    json_metadata: dict[str, Any] = {
        "filter_immune_slices": [],
        "filter_immune_slice_fields": {"4": ["col1", "col2"]},
    }
    
    filter_box = Slice()
    filter_box.id = 1
    filter_box.params = '{"filter_configs": [{"column": "col1"}]}'
    
    result = convert_filter_scopes(json_metadata, [filter_box])
    
    assert result[1]["col1"]["immune"] == [4]


def test_convert_filter_scopes_date_filter() -> None:
    """Test convert_filter_scopes with date filter."""
    json_metadata: dict[str, Any] = {
        "filter_immune_slices": [],
        "filter_immune_slice_fields": {},
    }
    
    filter_box = Slice()
    filter_box.id = 1
    filter_box.params = '{"date_filter": true}'
    
    result = convert_filter_scopes(json_metadata, [filter_box])
    
    assert "__time_range" in result[1]
    assert result[1]["__time_range"]["scope"] == ["ROOT_ID"]


def test_convert_filter_scopes_time_column() -> None:
    """Test convert_filter_scopes with time column."""
    json_metadata: dict[str, Any] = {
        "filter_immune_slices": [],
        "filter_immune_slice_fields": {},
    }
    
    filter_box = Slice()
    filter_box.id = 1
    filter_box.params = '{"show_sqla_time_column": true}'
    
    result = convert_filter_scopes(json_metadata, [filter_box])
    
    assert "__time_col" in result[1]


def test_convert_filter_scopes_time_granularity() -> None:
    """Test convert_filter_scopes with time granularity."""
    json_metadata: dict[str, Any] = {
        "filter_immune_slices": [],
        "filter_immune_slice_fields": {},
    }
    
    filter_box = Slice()
    filter_box.id = 1
    filter_box.params = '{"show_sqla_time_granularity": true}'
    
    result = convert_filter_scopes(json_metadata, [filter_box])
    
    assert "__time_grain" in result[1]


def test_convert_filter_scopes_invalid_field() -> None:
    """Test convert_filter_scopes handles invalid filter fields."""
    json_metadata: dict[str, Any] = {
        "filter_immune_slices": [],
        "filter_immune_slice_fields": {},
    }
    
    filter_box = Slice()
    filter_box.id = 1
    filter_box.params = '{"filter_configs": [{"column": 123}]}'
    
    result = convert_filter_scopes(json_metadata, [filter_box])
    
    # Should not add invalid field
    assert 1 not in result or len(result[1]) == 0


def test_convert_filter_scopes_empty_params() -> None:
    """Test convert_filter_scopes with empty params."""
    json_metadata: dict[str, Any] = {
        "filter_immune_slices": [],
        "filter_immune_slice_fields": {},
    }
    
    filter_box = Slice()
    filter_box.id = 1
    filter_box.params = '{}'
    
    result = convert_filter_scopes(json_metadata, [filter_box])
    
    # Should not add entry if no filters
    assert 1 not in result


def test_copy_filter_scopes_basic() -> None:
    """Test copy_filter_scopes with basic ID mapping."""
    old_filter_scopes = {
        1: {"col1": {"scope": ["ROOT_ID"], "immune": [2, 3]}},
    }
    old_to_new_slc_id_dict = {1: 10, 2: 20, 3: 30}
    
    result = copy_filter_scopes(old_to_new_slc_id_dict, old_filter_scopes)
    
    assert "10" in result
    assert result["10"]["col1"]["scope"] == ["ROOT_ID"]
    assert result["10"]["col1"]["immune"] == [20, 30]


def test_copy_filter_scopes_missing_mapping() -> None:
    """Test copy_filter_scopes when some IDs are not in mapping."""
    old_filter_scopes = {
        1: {"col1": {"scope": ["ROOT_ID"], "immune": [2, 3, 99]}},
    }
    old_to_new_slc_id_dict = {1: 10, 2: 20, 3: 30}
    
    result = copy_filter_scopes(old_to_new_slc_id_dict, old_filter_scopes)
    
    # Should only map IDs that exist in the mapping
    assert result["10"]["col1"]["immune"] == [20, 30]
    assert 99 not in result["10"]["col1"]["immune"]


def test_copy_filter_scopes_filter_id_not_mapped() -> None:
    """Test copy_filter_scopes when filter ID itself is not mapped."""
    old_filter_scopes = {
        99: {"col1": {"scope": ["ROOT_ID"], "immune": []}},
    }
    old_to_new_slc_id_dict = {1: 10}
    
    result = copy_filter_scopes(old_to_new_slc_id_dict, old_filter_scopes)
    
    # Should not include unmapped filter ID
    assert "99" not in result
    assert len(result) == 0


def test_copy_filter_scopes_empty_immune() -> None:
    """Test copy_filter_scopes with empty immune list."""
    old_filter_scopes = {
        1: {"col1": {"scope": ["ROOT_ID"], "immune": []}},
    }
    old_to_new_slc_id_dict = {1: 10}
    
    result = copy_filter_scopes(old_to_new_slc_id_dict, old_filter_scopes)
    
    assert result["10"]["col1"]["immune"] == []
