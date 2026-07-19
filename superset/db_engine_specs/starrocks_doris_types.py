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

"""Custom SQLAlchemy column types shared by the Apache Doris and StarRocks engine
specs. StarRocks was forked from Doris, so both expose the same set of
non-standard column types; they are declared once here and re-exported from each
engine spec module.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Float, Integer, Numeric
from sqlalchemy.sql.type_api import TypeEngine


class TINYINT(Integer):
    __visit_name__ = "TINYINT"


class LARGEINT(Integer):
    __visit_name__ = "LARGEINT"


class DOUBLE(Float):
    __visit_name__ = "DOUBLE"


class HLL(Numeric):
    __visit_name__ = "HLL"


class BITMAP(Numeric):
    __visit_name__ = "BITMAP"


class ARRAY(TypeEngine):
    __visit_name__ = "ARRAY"

    @property
    def python_type(self) -> type[list[Any]] | None:
        return list


class MAP(TypeEngine):
    __visit_name__ = "MAP"

    @property
    def python_type(self) -> type[dict[Any, Any]] | None:
        return dict


class STRUCT(TypeEngine):
    __visit_name__ = "STRUCT"

    @property
    def python_type(self) -> type[Any] | None:
        return None
