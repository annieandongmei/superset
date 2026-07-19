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

import pytest
from marshmallow.exceptions import ValidationError

from superset.commands.base import BaseCommand
from superset.commands.exceptions import CommandInvalidError
from superset.commands.importers.dispatcher import BaseImportDispatcherCommand
from superset.commands.importers.exceptions import IncorrectVersionError


class MockCommandV1(BaseCommand):
    """Mock command for testing."""

    def __init__(self, contents: dict[str, str], *args, **kwargs):
        self.contents = contents
        self.args = args
        self.kwargs = kwargs

    def run(self) -> None:
        if self.contents.get("version") == "v1":
            return
        raise IncorrectVersionError("Not v1")

    def validate(self) -> None:
        pass


class MockCommandV2(BaseCommand):
    """Mock command for testing."""

    def __init__(self, contents: dict[str, str], *args, **kwargs):
        self.contents = contents
        self.args = args
        self.kwargs = kwargs

    def run(self) -> None:
        if self.contents.get("version") == "v2":
            return
        raise IncorrectVersionError("Not v2")

    def validate(self) -> None:
        pass


class MockCommandInvalid(BaseCommand):
    """Mock command that raises CommandInvalidError."""

    def __init__(self, contents: dict[str, str], *args, **kwargs):
        self.contents = contents
        self.args = args
        self.kwargs = kwargs

    def run(self) -> None:
        raise CommandInvalidError("Invalid data")

    def validate(self) -> None:
        pass


class MockCommandValidationError(BaseCommand):
    """Mock command that raises ValidationError."""

    def __init__(self, contents: dict[str, str], *args, **kwargs):
        self.contents = contents
        self.args = args
        self.kwargs = kwargs

    def run(self) -> None:
        raise ValidationError("Validation failed")

    def validate(self) -> None:
        pass


class MockCommandUnexpectedError(BaseCommand):
    """Mock command that raises an unexpected error."""

    def __init__(self, contents: dict[str, str], *args, **kwargs):
        self.contents = contents
        self.args = args
        self.kwargs = kwargs

    def run(self) -> None:
        raise RuntimeError("Unexpected error")

    def validate(self) -> None:
        pass


class TestDispatcher(BaseImportDispatcherCommand):
    """Test dispatcher implementation."""

    command_versions = [MockCommandV1, MockCommandV2]


class TestBaseImportDispatcherCommand:
    def test_first_matching_version_selected(self) -> None:
        """Test that the first matching version is selected and executed."""
        dispatcher = TestDispatcher({"version": "v1"})
        dispatcher.run()  # Should not raise

    def test_second_matching_version_selected(self) -> None:
        """Test that the second matching version is selected if first doesn't match."""
        dispatcher = TestDispatcher({"version": "v2"})
        dispatcher.run()  # Should not raise

    def test_command_invalid_error_when_no_version_matches(self) -> None:
        """Test that CommandInvalidError is raised when no version matches."""
        dispatcher = TestDispatcher({"version": "v3"})
        with pytest.raises(CommandInvalidError) as exc_info:
            dispatcher.run()
        assert "Could not find a valid command to import file" in str(exc_info.value)

    def test_command_invalid_error_re_raised(self) -> None:
        """Test that CommandInvalidError from matched version is re-raised."""
        TestDispatcher.command_versions = [MockCommandInvalid]
        dispatcher = TestDispatcher({"version": "v1"})
        with pytest.raises(CommandInvalidError) as exc_info:
            dispatcher.run()
        assert "Invalid data" in str(exc_info.value)
        TestDispatcher.command_versions = [MockCommandV1, MockCommandV2]  # Reset

    def test_validation_error_re_raised(self) -> None:
        """Test that ValidationError from matched version is re-raised."""
        TestDispatcher.command_versions = [MockCommandValidationError]
        dispatcher = TestDispatcher({"version": "v1"})
        with pytest.raises(ValidationError) as exc_info:
            dispatcher.run()
        assert "Validation failed" in str(exc_info.value)
        TestDispatcher.command_versions = [MockCommandV1, MockCommandV2]  # Reset

    def test_unexpected_error_propagated(self) -> None:
        """Test that unexpected errors are propagated."""
        TestDispatcher.command_versions = [MockCommandUnexpectedError]
        dispatcher = TestDispatcher({"version": "v1"})
        with pytest.raises(RuntimeError) as exc_info:
            dispatcher.run()
        assert "Unexpected error" in str(exc_info.value)
        TestDispatcher.command_versions = [MockCommandV1, MockCommandV2]  # Reset

    def test_validate_passes(self) -> None:
        """Test that validate() passes by default."""
        dispatcher = TestDispatcher({"version": "v1"})
        dispatcher.validate()  # Should not raise

    def test_args_and_kwargs_passed_to_version_command(self) -> None:
        """Test that args and kwargs are passed to the version command."""

        class MockCommandWithArgs(BaseCommand):
            def __init__(self, contents: dict[str, str], *args, **kwargs):
                self.contents = contents
                self.args = args
                self.kwargs = kwargs

            def run(self) -> None:
                if self.args == ("arg1", "arg2") and self.kwargs == {"key": "value"}:
                    return
                raise IncorrectVersionError("Args don't match")

            def validate(self) -> None:
                pass

        TestDispatcher.command_versions = [MockCommandWithArgs]
        dispatcher = TestDispatcher({"version": "v1"}, "arg1", "arg2", key="value")
        dispatcher.run()  # Should not raise
        TestDispatcher.command_versions = [MockCommandV1, MockCommandV2]  # Reset
