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
from unittest import mock

from pytest_mock import MockerFixture

from superset.commands.tag.utils import validate_object_access
from superset.exceptions import SupersetSecurityException
from superset.tags.models import ObjectType


class _StubError(Exception):
    pass


def _patch_security_manager(mocker: MockerFixture) -> mock.MagicMock:
    return mocker.patch(
        "superset.commands.tag.utils.security_manager",
        new_callable=mock.MagicMock,
    )


def test_validate_object_access_stale_reference(mocker: MockerFixture) -> None:
    mocker.patch("superset.commands.tag.utils.to_object_model", return_value=None)
    sm = _patch_security_manager(mocker)

    exceptions: list[Any] = []
    validate_object_access(ObjectType.chart, 1, exceptions, _StubError)

    assert exceptions == []
    sm.raise_for_access.assert_not_called()


def test_validate_object_access_granted(mocker: MockerFixture) -> None:
    target = object()
    mocker.patch("superset.commands.tag.utils.to_object_model", return_value=target)
    sm = _patch_security_manager(mocker)

    exceptions: list[Any] = []
    validate_object_access(ObjectType.dataset, 7, exceptions, _StubError)

    assert exceptions == []
    sm.raise_for_access.assert_called_once_with(datasource=target)


def test_validate_object_access_denied_uses_error_factory(
    mocker: MockerFixture,
) -> None:
    target = object()
    mocker.patch("superset.commands.tag.utils.to_object_model", return_value=target)
    sm = _patch_security_manager(mocker)
    sm.raise_for_access.side_effect = SupersetSecurityException(mock.Mock())

    exceptions: list[Any] = []
    validate_object_access(ObjectType.dashboard, 42, exceptions, _StubError)

    assert len(exceptions) == 1
    assert isinstance(exceptions[0], _StubError)
    assert "Access denied for" in str(exceptions[0])
    assert "42" in str(exceptions[0])


def test_validate_object_access_unsupported_type(mocker: MockerFixture) -> None:
    target = object()
    mocker.patch("superset.commands.tag.utils.to_object_model", return_value=target)
    sm = _patch_security_manager(mocker)

    exceptions: list[Any] = []
    validate_object_access(mock.Mock(name="unknown_type"), 1, exceptions, _StubError)

    assert len(exceptions) == 1
    assert isinstance(exceptions[0], _StubError)
    assert "Access validation not supported" in str(exceptions[0])
    sm.raise_for_access.assert_not_called()
