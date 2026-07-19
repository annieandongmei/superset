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

from pytest_mock import MockerFixture

from superset.charts.data.api import ChartDataRestApi
from superset.common.chart_data import ChartDataResultFormat, ChartDataResultType
from superset.constants import CACHE_DISABLED_TIMEOUT
from superset.exceptions import (
    QueryObjectValidationError,
    SupersetSecurityException,
)


def _build_query_context(
    *,
    result_format: ChartDataResultFormat = ChartDataResultFormat.JSON,
    result_type: ChartDataResultType = ChartDataResultType.FULL,
    cache_timeout: int = 300,
) -> MagicMock:
    query_context = MagicMock()
    query_context.result_format = result_format
    query_context.result_type = result_type
    query_context.get_cache_timeout.return_value = cache_timeout
    return query_context


def test_create_and_validate_command_success(mocker: MockerFixture) -> None:
    command_cls = mocker.patch("superset.charts.data.api.ChartDataCommand")
    api = MagicMock()
    query_context = object()
    api._create_query_context_from_form.return_value = query_context

    result = ChartDataRestApi._create_and_validate_command(api, {"a": 1})

    assert result == (query_context, command_cls.return_value)
    command_cls.return_value.validate.assert_called_once_with()


def test_create_and_validate_command_security_exception(
    mocker: MockerFixture,
) -> None:
    command_cls = mocker.patch("superset.charts.data.api.ChartDataCommand")
    command_cls.return_value.validate.side_effect = SupersetSecurityException(
        MagicMock()
    )
    api = MagicMock()

    result = ChartDataRestApi._create_and_validate_command(api, {})

    assert result == api.response_403.return_value


def test_create_and_validate_command_query_object_error(
    mocker: MockerFixture,
) -> None:
    command_cls = mocker.patch("superset.charts.data.api.ChartDataCommand")
    command_cls.return_value.validate.side_effect = QueryObjectValidationError("bad")
    api = MagicMock()

    result = ChartDataRestApi._create_and_validate_command(api, {})

    assert result == api.response_400.return_value


def test_should_run_async_true(mocker: MockerFixture) -> None:
    mocker.patch("superset.charts.data.api.is_feature_enabled", return_value=True)
    api = MagicMock()

    assert ChartDataRestApi._should_run_async(api, _build_query_context()) is True


def test_should_run_async_false_when_flag_disabled(mocker: MockerFixture) -> None:
    mocker.patch("superset.charts.data.api.is_feature_enabled", return_value=False)
    api = MagicMock()

    assert ChartDataRestApi._should_run_async(api, _build_query_context()) is False


def test_should_run_async_false_when_cache_disabled(mocker: MockerFixture) -> None:
    mocker.patch("superset.charts.data.api.is_feature_enabled", return_value=True)
    api = MagicMock()
    query_context = _build_query_context(cache_timeout=CACHE_DISABLED_TIMEOUT)

    assert ChartDataRestApi._should_run_async(api, query_context) is False


def test_should_run_async_false_for_non_json_format(mocker: MockerFixture) -> None:
    mocker.patch("superset.charts.data.api.is_feature_enabled", return_value=True)
    api = MagicMock()
    query_context = _build_query_context(result_format=ChartDataResultFormat.CSV)

    assert ChartDataRestApi._should_run_async(api, query_context) is False
