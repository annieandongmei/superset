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

from typing import ClassVar

import pytest
from marshmallow.exceptions import ValidationError

from superset.commands.base import BaseCommand
from superset.commands.exceptions import CommandInvalidError
from superset.commands.importers.dispatcher import (
    BaseImportDispatcherCommand,
    ImportCommandFactory,
)
from superset.commands.importers.exceptions import IncorrectVersionError


def _make_command(mock):
    class _Command(BaseCommand):
        def __init__(self, contents, *args, **kwargs):
            self.contents = contents
            self.args = args
            self.kwargs = kwargs

        def run(self):
            return mock(self.contents, *self.args, **self.kwargs)

        def validate(self):
            pass

    return _Command


def test_dispatch_uses_first_matching_version(mocker):
    """The first version that does not raise IncorrectVersionError handles it."""
    first = mocker.Mock(side_effect=IncorrectVersionError())
    second = mocker.Mock(return_value=None)
    third = mocker.Mock(return_value=None)

    class Dispatcher(BaseImportDispatcherCommand):
        command_versions: ClassVar[list[ImportCommandFactory]] = [
            _make_command(first),
            _make_command(second),
            _make_command(third),
        ]

    Dispatcher({"file": "contents"}, key="value").run()

    first.assert_called_once_with({"file": "contents"}, key="value")
    second.assert_called_once_with({"file": "contents"}, key="value")
    third.assert_not_called()


def test_dispatch_raises_when_no_version_matches(mocker):
    """When every version rejects the file, a CommandInvalidError is raised."""
    version = mocker.Mock(side_effect=IncorrectVersionError())

    class Dispatcher(BaseImportDispatcherCommand):
        command_versions: ClassVar[list[ImportCommandFactory]] = [
            _make_command(version)
        ]

    with pytest.raises(CommandInvalidError):
        Dispatcher({}).run()


@pytest.mark.parametrize("error", [CommandInvalidError(), ValidationError("bad")])
def test_dispatch_reraises_validation_errors(mocker, error):
    """A matched-but-invalid file surfaces its validation error to the caller."""
    version = mocker.Mock(side_effect=error)

    class Dispatcher(BaseImportDispatcherCommand):
        command_versions: ClassVar[list[ImportCommandFactory]] = [
            _make_command(version)
        ]

    with pytest.raises(type(error)):
        Dispatcher({}).run()


def test_dispatch_reraises_unexpected_errors(mocker):
    """Unexpected errors after a version matches are propagated."""
    version = mocker.Mock(side_effect=RuntimeError("boom"))

    class Dispatcher(BaseImportDispatcherCommand):
        command_versions: ClassVar[list[ImportCommandFactory]] = [
            _make_command(version)
        ]

    with pytest.raises(RuntimeError):
        Dispatcher({}).run()
