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

from pathlib import Path
from unittest.mock import patch

from superset.extensions import UIManifestProcessor


class TestUIManifestProcessor:
    def test_parse_manifest_json_missing_file_logs_debug(self, tmp_path: Path) -> None:
        """Test that missing manifest file logs debug message."""
        processor = UIManifestProcessor(str(tmp_path))
        with patch("superset.extensions.logger") as mock_logger:
            processor.parse_manifest_json()
            mock_logger.debug.assert_called_once()
            assert "not found" in mock_logger.debug.call_args[0][0]

    def test_parse_manifest_json_malformed_json_logs_warning(
        self, tmp_path: Path
    ) -> None:
        """Test that malformed manifest file logs warning."""
        manifest_file = tmp_path / "static" / "assets" / "manifest.json"
        manifest_file.parent.mkdir(parents=True, exist_ok=True)
        manifest_file.write_text("{ invalid json }")

        processor = UIManifestProcessor(str(tmp_path))
        with patch("superset.extensions.logger") as mock_logger:
            processor.parse_manifest_json()
            mock_logger.warning.assert_called_once()
            assert "Failed to parse" in mock_logger.warning.call_args[0][0]

    def test_parse_manifest_json_valid_json_succeeds(self, tmp_path: Path) -> None:
        """Test that valid manifest file is parsed correctly."""
        manifest_file = tmp_path / "static" / "assets" / "manifest.json"
        manifest_file.parent.mkdir(parents=True, exist_ok=True)
        manifest_file.write_text('{"entrypoints": {"main": {"js": ["app.js"]}}}')

        processor = UIManifestProcessor(str(tmp_path))
        with patch("superset.extensions.logger") as mock_logger:
            processor.parse_manifest_json()
            assert processor.manifest == {"main": {"js": ["app.js"]}}
            mock_logger.debug.assert_not_called()
            mock_logger.warning.assert_not_called()
