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

"""Unit tests for the shared semantic-layer compatibility helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from superset.errors import ErrorLevel, SupersetError, SupersetErrorType
from superset.exceptions import SupersetSecurityException
from superset.mcp_service.semantic_layer.schemas import SemanticLayerError
from superset.mcp_service.semantic_layer.tool import _common

_COMMON = "superset.mcp_service.semantic_layer.tool._common"


def test_check_metadata_permission_allows() -> None:
    with patch(f"{_COMMON}.user_can_view_data_model_metadata", return_value=True):
        assert _common.check_metadata_permission() is None


def test_check_metadata_permission_denies() -> None:
    with patch(f"{_COMMON}.user_can_view_data_model_metadata", return_value=False):
        error = _common.check_metadata_permission()
    assert isinstance(error, SemanticLayerError)
    assert error.error_type == "DataModelMetadataRestricted"


def test_validate_selection_target_requires_one() -> None:
    error = _common.validate_selection_target(None, None)
    assert isinstance(error, SemanticLayerError)
    assert error.error_type == "ValidationError"


def test_validate_selection_target_rejects_both() -> None:
    error = _common.validate_selection_target(1, 2)
    assert isinstance(error, SemanticLayerError)
    assert error.error_type == "ValidationError"


def test_validate_selection_target_accepts_exactly_one() -> None:
    assert _common.validate_selection_target(1, None) is None
    assert _common.validate_selection_target(None, 2) is None


def test_load_builtin_dataset_not_found() -> None:
    with patch(
        "superset.daos.dataset.DatasetDAO.find_by_id",
        return_value=None,
    ):
        result = _common.load_builtin_dataset(999, action="test")
    assert isinstance(result, SemanticLayerError)
    assert result.error_type == "NotFound"


def test_load_builtin_dataset_found() -> None:
    dataset = MagicMock()
    with patch(
        "superset.daos.dataset.DatasetDAO.find_by_id",
        return_value=dataset,
    ):
        result = _common.load_builtin_dataset(1, action="test")
    assert result is dataset


def test_validate_builtin_selection_unknown_names() -> None:
    dataset = MagicMock()
    dataset.metrics = [_named("metric_name", "count")]
    dataset.columns = [_named("column_name", "region")]
    error = _common.validate_builtin_selection(dataset, ["bogus_metric"], [])
    assert isinstance(error, SemanticLayerError)
    assert error.error_type == "ValidationError"
    assert "bogus_metric" in error.error


def test_validate_builtin_selection_all_valid() -> None:
    dataset = MagicMock()
    dataset.metrics = [_named("metric_name", "count")]
    dataset.columns = [_named("column_name", "region")]
    assert _common.validate_builtin_selection(dataset, ["count"], ["region"]) is None


def test_load_external_view_not_found() -> None:
    with patch(
        "superset.daos.semantic_layer.SemanticViewDAO.find_by_id",
        return_value=None,
    ):
        result = _common.load_external_view(999, action="test")
    assert isinstance(result, SemanticLayerError)
    assert result.error_type == "NotFound"


def test_load_external_view_access_denied() -> None:
    view = MagicMock()
    view.raise_for_access.side_effect = SupersetSecurityException(
        SupersetError(
            message="nope",
            error_type=SupersetErrorType.MISSING_OWNERSHIP_ERROR,
            level=ErrorLevel.ERROR,
        )
    )
    with patch(
        "superset.daos.semantic_layer.SemanticViewDAO.find_by_id",
        return_value=view,
    ):
        result = _common.load_external_view(5, action="test")
    assert isinstance(result, SemanticLayerError)
    assert result.error_type == "AccessDenied"


def test_load_external_view_ok() -> None:
    view = MagicMock()
    with patch(
        "superset.daos.semantic_layer.SemanticViewDAO.find_by_id",
        return_value=view,
    ):
        result = _common.load_external_view(5, action="test")
    assert result is view
    view.raise_for_access.assert_called_once()


def _named(attr: str, value: str) -> MagicMock:
    return MagicMock(**{attr: value})
