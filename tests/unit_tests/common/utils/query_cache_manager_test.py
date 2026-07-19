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

from typing import Any
from unittest.mock import MagicMock

import pytest
from flask import g
from pandas import DataFrame
from pytest_mock import MockerFixture

from superset.common.db_query_status import QueryStatus
from superset.common.utils import query_cache_manager as qcm_module
from superset.common.utils.query_cache_manager import QueryCacheManager
from superset.constants import CacheRegion
from superset.exceptions import CacheLoadError

MODULE = "superset.common.utils.query_cache_manager"


def _fake_query_result(status: str = QueryStatus.SUCCESS) -> MagicMock:
    result = MagicMock()
    result.status = status
    result.query = "SELECT 1"
    result.applied_template_filters = ["f1"]
    result.applied_filter_columns = ["c1"]
    result.rejected_filter_columns = ["c2"]
    result.error_message = None
    result.df = DataFrame({"a": [1, 2]})
    result.sql_rowcount = 2
    return result


def test_init_defaults() -> None:
    manager = QueryCacheManager()
    assert manager.df.empty
    assert manager.query == ""
    assert manager.annotation_data == {}
    assert manager.applied_template_filters == []
    assert manager.applied_filter_columns == []
    assert manager.rejected_filter_columns == []
    assert manager.is_loaded is False
    assert manager.bq_memory_limited is False
    assert manager.bq_memory_limited_row_count == 0


def test_stats_logger_reads_from_app_config(app_context: None) -> None:
    manager = QueryCacheManager()
    assert manager.stats_logger is not None


def test_set_only_when_key_present(mocker: MockerFixture) -> None:
    set_and_log = mocker.patch(f"{MODULE}.set_and_log_cache")

    QueryCacheManager.set(None, {"df": DataFrame()})
    set_and_log.assert_not_called()

    QueryCacheManager.set("k", {"df": DataFrame()}, timeout=10, datasource_uid="1__t")
    set_and_log.assert_called_once()


def test_delete_only_when_key_present(mocker: MockerFixture) -> None:
    fake_cache = MagicMock()
    mocker.patch.dict(qcm_module._cache, {CacheRegion.DEFAULT: fake_cache})

    QueryCacheManager.delete(None)
    fake_cache.delete.assert_not_called()

    QueryCacheManager.delete("k")
    fake_cache.delete.assert_called_once_with("k")


def test_has_key(mocker: MockerFixture) -> None:
    fake_cache = MagicMock()
    mocker.patch.dict(qcm_module._cache, {CacheRegion.DEFAULT: fake_cache})

    assert QueryCacheManager.has(None) is False

    fake_cache.get.return_value = {"df": DataFrame()}
    assert QueryCacheManager.has("k") is True

    fake_cache.get.return_value = None
    assert QueryCacheManager.has("k") is False


def test_get_returns_empty_when_no_key(mocker: MockerFixture) -> None:
    fake_cache = MagicMock()
    mocker.patch.dict(qcm_module._cache, {CacheRegion.DEFAULT: fake_cache})
    manager = QueryCacheManager.get(None)
    assert manager.is_loaded is False
    fake_cache.get.assert_not_called()


def test_get_returns_empty_when_force_query(mocker: MockerFixture) -> None:
    fake_cache = MagicMock()
    mocker.patch.dict(qcm_module._cache, {CacheRegion.DEFAULT: fake_cache})
    manager = QueryCacheManager.get("k", force_query=True)
    assert manager.is_loaded is False
    fake_cache.get.assert_not_called()


def test_get_cache_hit_populates_fields(
    app_context: None, mocker: MockerFixture
) -> None:
    cache_value: dict[str, Any] = {
        "df": DataFrame({"a": [1]}),
        "query": "SELECT 1",
        "annotation_data": {"x": 1},
        "applied_template_filters": ["f"],
        "applied_filter_columns": ["c"],
        "rejected_filter_columns": ["r"],
        "sql_rowcount": 1,
        "dttm": "2021-01-01T00:00:00",
        "queried_dttm": "2021-01-01T00:00:00",
    }
    fake_cache = MagicMock()
    fake_cache.get.return_value = cache_value
    mocker.patch.dict(qcm_module._cache, {CacheRegion.DEFAULT: fake_cache})

    manager = QueryCacheManager.get("k")
    assert manager.is_loaded is True
    assert manager.is_cached is True
    assert manager.status == QueryStatus.SUCCESS
    assert manager.query == "SELECT 1"
    assert manager.annotation_data == {"x": 1}
    assert manager.cache_dttm == "2021-01-01T00:00:00"
    assert manager.sql_rowcount == 1


def test_get_cache_hit_missing_required_key_is_handled(
    app_context: None, mocker: MockerFixture
) -> None:
    # missing "query" triggers KeyError handling; manager stays not loaded
    fake_cache = MagicMock()
    fake_cache.get.return_value = {"df": DataFrame()}
    mocker.patch.dict(qcm_module._cache, {CacheRegion.DEFAULT: fake_cache})

    manager = QueryCacheManager.get("k")
    assert manager.is_loaded is False


def test_get_force_cached_miss_raises(app_context: None, mocker: MockerFixture) -> None:
    fake_cache = MagicMock()
    fake_cache.get.return_value = None
    mocker.patch.dict(qcm_module._cache, {CacheRegion.DEFAULT: fake_cache})

    with pytest.raises(CacheLoadError):
        QueryCacheManager.get("k", force_cached=True)


def test_set_query_result_success_sets_and_loads(
    app_context: None, mocker: MockerFixture
) -> None:
    set_spy = mocker.patch.object(QueryCacheManager, "set")
    manager = QueryCacheManager()
    manager.set_query_result("k", _fake_query_result())

    assert manager.is_loaded is True
    assert manager.status == QueryStatus.SUCCESS
    assert manager.query == "SELECT 1"
    assert manager.queried_dttm is not None
    set_spy.assert_called_once()


def test_set_query_result_captures_bq_memory_flag(
    app: Any, mocker: MockerFixture
) -> None:
    mocker.patch.object(QueryCacheManager, "set")
    with app.test_request_context():
        g.bq_memory_limited = True
        g.bq_memory_limited_row_count = 5
        manager = QueryCacheManager()
        manager.set_query_result("k", _fake_query_result())

        assert manager.bq_memory_limited is True
        assert manager.bq_memory_limited_row_count == 5
        # flags are reset on ``g`` after capture
        assert g.bq_memory_limited is False
        assert g.bq_memory_limited_row_count == 0


def test_set_query_result_failed_status_does_not_load(
    app_context: None, mocker: MockerFixture
) -> None:
    set_spy = mocker.patch.object(QueryCacheManager, "set")
    manager = QueryCacheManager()
    manager.set_query_result("k", _fake_query_result(status=QueryStatus.FAILED))

    assert manager.is_loaded is False
    set_spy.assert_not_called()


def test_set_query_result_handles_exception(
    app_context: None, mocker: MockerFixture
) -> None:
    manager = QueryCacheManager()
    broken = MagicMock()
    # accessing .status raises to force the except branch
    type(broken).status = property(
        lambda self: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    manager.set_query_result("k", broken)

    assert manager.status == QueryStatus.FAILED
    assert manager.error_message == "boom"
