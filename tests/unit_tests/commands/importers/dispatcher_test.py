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

import pytest
from marshmallow.exceptions import ValidationError

from superset.commands.exceptions import CommandInvalidError
from superset.commands.importers.dispatcher import BaseImportCommand
from superset.commands.importers.exceptions import IncorrectVersionError


def _make_command(behavior: Exception | None) -> MagicMock:
    """Return a factory that mimics a versioned import command class."""
    instance = MagicMock()
    if behavior is not None:
        instance.run.side_effect = behavior
    factory = MagicMock(return_value=instance)
    factory._instance = instance
    return factory


def test_dispatch_stops_at_first_matching_version() -> None:
    """The dispatcher stops iterating once a version handles the contents."""
    first = _make_command(None)
    second = _make_command(None)

    class Dispatcher(BaseImportCommand):
        command_versions = [first, second]

    contents = {"file.yaml": "content"}
    Dispatcher(contents).run()

    first.assert_called_once_with(contents)
    first._instance.run.assert_called_once()
    second.assert_not_called()


def test_dispatch_skips_incorrect_version() -> None:
    """A version raising IncorrectVersionError is skipped for the next one."""
    first = _make_command(IncorrectVersionError("nope"))
    second = _make_command(None)

    class Dispatcher(BaseImportCommand):
        command_versions = [first, second]

    Dispatcher({"file.yaml": "content"}).run()

    first._instance.run.assert_called_once()
    second._instance.run.assert_called_once()


def test_dispatch_passes_args_and_kwargs() -> None:
    """Positional and keyword args are forwarded to the versioned command."""
    version = _make_command(None)

    class Dispatcher(BaseImportCommand):
        command_versions = [version]

    contents = {"file.yaml": "content"}
    Dispatcher(contents, "arg", overwrite=True).run()

    version.assert_called_once_with(contents, "arg", overwrite=True)


@pytest.mark.parametrize(
    "error",
    [CommandInvalidError("invalid"), ValidationError("invalid")],
)
def test_dispatch_reraises_validation_errors(error: Exception) -> None:
    """A matched-but-invalid file propagates the validation error."""
    version = _make_command(error)

    class Dispatcher(BaseImportCommand):
        command_versions = [version]

    with pytest.raises(type(error)):
        Dispatcher({"file.yaml": "content"}).run()


def test_dispatch_reraises_unexpected_errors() -> None:
    """Unexpected errors bubble up instead of being swallowed."""
    version = _make_command(RuntimeError("boom"))

    class Dispatcher(BaseImportCommand):
        command_versions = [version]

    with pytest.raises(RuntimeError):
        Dispatcher({"file.yaml": "content"}).run()


def test_dispatch_no_matching_version() -> None:
    """When no version matches, a CommandInvalidError is raised."""
    version = _make_command(IncorrectVersionError("nope"))

    class Dispatcher(BaseImportCommand):
        command_versions = [version]

    with pytest.raises(CommandInvalidError):
        Dispatcher({"file.yaml": "content"}).run()


def test_all_dispatchers_share_base() -> None:
    """Every resource dispatcher reuses the shared base implementation."""
    from superset.commands.chart.importers.dispatcher import ImportChartsCommand
    from superset.commands.dashboard.importers.dispatcher import (
        ImportDashboardsCommand,
    )
    from superset.commands.database.importers.dispatcher import (
        ImportDatabasesCommand,
    )
    from superset.commands.dataset.importers.dispatcher import ImportDatasetsCommand
    from superset.commands.query.importers.dispatcher import (
        ImportSavedQueriesCommand,
    )
    from superset.commands.theme.importers.dispatcher import ImportThemesCommand

    dispatchers = [
        ImportChartsCommand,
        ImportDashboardsCommand,
        ImportDatabasesCommand,
        ImportDatasetsCommand,
        ImportSavedQueriesCommand,
        ImportThemesCommand,
    ]
    for dispatcher in dispatchers:
        assert issubclass(dispatcher, BaseImportCommand)
        assert dispatcher.run is BaseImportCommand.run
        assert dispatcher.command_versions
