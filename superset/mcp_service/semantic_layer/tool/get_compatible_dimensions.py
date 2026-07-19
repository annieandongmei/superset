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

"""MCP tool: get_compatible_dimensions

Returns dimensions compatible with the current metric/dimension selection.
"""

import logging

from fastmcp import Context
from superset_core.mcp.decorators import tool, ToolAnnotations

from superset.mcp_service.privacy import requires_data_model_metadata_access
from superset.mcp_service.semantic_layer.schemas import (
    CompatibleDimensionsResponse,
    DimensionInfo,
    GetCompatibleDimensionsRequest,
    SemanticLayerError,
)
from superset.mcp_service.semantic_layer.tool._common import (
    check_metadata_permission,
    load_builtin_dataset,
    load_external_view,
    validate_builtin_selection,
    validate_selection_target,
)

logger = logging.getLogger(__name__)


@tool(
    tags=["data", "semantic"],
    class_permission_name="Dataset",
    annotations=ToolAnnotations(
        title="Get compatible dimensions",
        readOnlyHint=True,
        destructiveHint=False,
    ),
)
@requires_data_model_metadata_access
async def get_compatible_dimensions(
    request: GetCompatibleDimensionsRequest,
    ctx: Context,
) -> CompatibleDimensionsResponse | SemanticLayerError:
    """Return dimensions compatible with the current metric/dimension selection.

    Used to drive progressive disclosure in query builders: after the user
    selects one or more metrics (and optionally some dimensions), this tool
    returns the dimensions that can validly be added without breaking the
    underlying query.

    Provide exactly one of ``dataset_id`` (built-in) or ``view_id`` (external).

    For built-in datasets, returns all groupby-enabled columns from the dataset.
    SQL datasets have no semantic compatibility constraints between metrics and
    dimensions, so all groupby columns are returned for any valid selection.
    Unknown names in ``selected_metrics`` or ``selected_dimensions`` are
    rejected with a ValidationError.

    For external semantic views, delegates to the view's
    ``get_compatible_dimensions`` implementation.

    Example:
    ```json
    {
        "selected_metrics": ["revenue"],
        "selected_dimensions": [],
        "view_id": 5
    }
    ```
    """
    await ctx.info(
        "Getting compatible dimensions: dataset_id=%s, view_id=%s, "
        "metrics=%s, dims=%s"
        % (
            request.dataset_id,
            request.view_id,
            request.selected_metrics,
            request.selected_dimensions,
        )
    )

    if permission_error := check_metadata_permission():
        return permission_error

    if target_error := validate_selection_target(request.dataset_id, request.view_id):
        return target_error

    try:
        # ------------------------------------------------------------------
        # Built-in dataset path
        # ------------------------------------------------------------------
        if request.dataset_id is not None:
            dataset = load_builtin_dataset(
                request.dataset_id,
                action="mcp.get_compatible_dimensions.builtin",
            )
            if isinstance(dataset, SemanticLayerError):
                return dataset

            if validation_error := validate_builtin_selection(
                dataset,
                request.selected_metrics,
                request.selected_dimensions,
            ):
                return validation_error

            # For built-in datasets all groupby columns are always compatible;
            # there's no per-metric compatibility constraint at the SQL level.
            dims: list[DimensionInfo] = [
                DimensionInfo(
                    name=col.column_name,
                    verbose_name=col.verbose_name or None,
                    description=col.description or None,
                    type=col.type or None,
                    is_dttm=bool(col.is_dttm),
                    groupby=bool(col.groupby),
                    filterable=bool(col.filterable),
                    source="builtin",
                )
                for col in dataset.columns
                if col.groupby
            ]

            await ctx.info("Compatible dimensions (builtin): count=%d" % len(dims))
            return CompatibleDimensionsResponse(
                compatible_dimensions=dims,
                source="builtin",
            )

        # ------------------------------------------------------------------
        # External semantic view path
        # ------------------------------------------------------------------
        from superset.semantic_layers.models import ColumnMetadata

        view_id: int = request.view_id  # type: ignore[assignment]
        view = load_external_view(
            view_id,
            action="mcp.get_compatible_dimensions.external",
        )
        if isinstance(view, SemanticLayerError):
            return view

        compatible_names: list[str] = view.get_compatible_dimensions(
            request.selected_metrics,
            request.selected_dimensions,
        )

        # Enrich with full column metadata
        all_cols: dict[str, ColumnMetadata] = {
            col.column_name: col for col in view.columns
        }
        dims = [
            DimensionInfo(
                name=name,
                verbose_name=all_cols[name].verbose_name if name in all_cols else None,
                description=all_cols[name].description if name in all_cols else None,
                type=all_cols[name].type if name in all_cols else None,
                is_dttm=all_cols[name].is_dttm if name in all_cols else False,
                groupby=all_cols[name].groupby if name in all_cols else True,
                filterable=all_cols[name].filterable if name in all_cols else True,
                source="external",
            )
            for name in compatible_names
        ]

        await ctx.info(
            "Compatible dimensions (external view id=%d): count=%d"
            % (view.id, len(dims))
        )
        return CompatibleDimensionsResponse(
            compatible_dimensions=dims,
            source="external",
        )

    except Exception as exc:
        logger.exception(
            "Unexpected error in get_compatible_dimensions: %s: %s",
            type(exc).__name__,
            str(exc),
        )
        await ctx.error("Unexpected error: %s: %s" % (type(exc).__name__, str(exc)))
        return SemanticLayerError.create(
            error=f"Internal error in get_compatible_dimensions: {exc}",
            error_type="InternalError",
        )
