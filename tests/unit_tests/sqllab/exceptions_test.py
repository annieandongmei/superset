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

from unittest.mock import MagicMock

from superset.errors import ErrorLevel, SupersetError, SupersetErrorType
from superset.sqllab.exceptions import (
    QUERY_IS_FORBIDDEN_TO_ACCESS_REASON_MESSAGE,
    QueryIsForbiddenToAccessException,
    SqlLabException,
)


def _ctx(details: str = "SELECT 1") -> MagicMock:
    ctx = MagicMock()
    ctx.get_query_details.return_value = details
    return ctx


def test_get_reason_from_reason_message() -> None:
    assert SqlLabException._get_reason(reason_message="boom") == ": boom"


def test_get_reason_from_exception_get_message() -> None:
    class GetMessageError(Exception):
        def get_message(self) -> str:
            return "custom message"

    assert (
        SqlLabException._get_reason(exception=GetMessageError()) == ": custom message"
    )


def test_get_reason_from_exception_message_attr() -> None:
    exc = Exception()
    exc.message = "attr message"  # type: ignore[attr-defined]
    assert SqlLabException._get_reason(exception=exc) == ": attr message"


def test_get_reason_from_exception_str() -> None:
    assert SqlLabException._get_reason(exception=ValueError("plain")) == ": plain"


def test_get_reason_empty_when_no_input() -> None:
    assert SqlLabException._get_reason() == ""


def test_message_includes_reason_and_suggestion(app_context: None) -> None:
    exc = SqlLabException(
        _ctx("SELECT 42"),
        reason_message="it failed",
        suggestion_help_msg="try again",
    )
    message = str(exc)
    assert "SELECT 42" in message
    assert "it failed" in message
    assert "try again" in message


def test_error_type_defaults_to_generic_backend_error(app_context: None) -> None:
    exc = SqlLabException(_ctx())
    assert exc.error_type == SupersetErrorType.GENERIC_BACKEND_ERROR


def test_error_type_taken_from_exception_error_type(app_context: None) -> None:
    inner = ValueError("x")
    inner.error_type = SupersetErrorType.CONNECTION_INVALID_HOSTNAME_ERROR  # type: ignore[attr-defined]
    exc = SqlLabException(_ctx(), exception=inner)
    assert exc.error_type == SupersetErrorType.CONNECTION_INVALID_HOSTNAME_ERROR


def test_error_type_taken_from_nested_superset_error(app_context: None) -> None:
    class WithError(Exception):
        error_type = None
        error = SupersetError(
            message="nested",
            error_type=SupersetErrorType.SQLLAB_TIMEOUT_ERROR,
            level=ErrorLevel.ERROR,
        )

    exc = SqlLabException(_ctx(), exception=WithError())
    assert exc.error_type == SupersetErrorType.SQLLAB_TIMEOUT_ERROR


def test_explicit_error_type_is_preserved(app_context: None) -> None:
    exc = SqlLabException(
        _ctx(),
        error_type=SupersetErrorType.QUERY_SECURITY_ACCESS_ERROR,
        exception=ValueError("ignored for error type"),
    )
    assert exc.error_type == SupersetErrorType.QUERY_SECURITY_ACCESS_ERROR


def test_query_is_forbidden_to_access_exception(app_context: None) -> None:
    exc = QueryIsForbiddenToAccessException(_ctx())
    assert exc.error_type == SupersetErrorType.QUERY_SECURITY_ACCESS_ERROR
    assert QUERY_IS_FORBIDDEN_TO_ACCESS_REASON_MESSAGE in str(exc)
