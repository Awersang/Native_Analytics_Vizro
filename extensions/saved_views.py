"""
Extension: Saved views  (detachable)
====================================

Adds a generic browser-local "saved views" panel for Dash/Vizro pages. The
extension discovers interactive controls from the built app/page layouts and
stores snapshots per browser pathname in ``dcc.Store(storage_type="local")``.
"""

from __future__ import annotations

import json
import logging
import re
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

import dash
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash import ALL, Input, Output, State, _callback as dash_callback, ctx, dcc, html, no_update
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate

logger = logging.getLogger(__name__)

STORE_ID = "saved-views-store"
LOCATION_ID = "saved-views-location"
DOWNLOAD_ID = "saved-views-download"
TOGGLE_ID = "saved-views-toggle"
PANEL_ID = "saved-views-panel"
SAVE_NAME_ID = "saved-views-name"
SAVE_BUTTON_ID = "saved-views-save"
LIST_ID = "saved-views-list"
STATUS_ID = "saved-views-status"

RESTORE_BUTTON_TYPE = "saved-views-restore"
RENAME_BUTTON_TYPE = "saved-views-rename"
RENAME_INPUT_TYPE = "saved-views-rename-input"
DELETE_BUTTON_TYPE = "saved-views-delete"
EXPORT_BUTTON_TYPE = "saved-views-export"

_SINGLE_VALUE_COMPONENTS = (
    dcc.Dropdown,
    dcc.Slider,
    dcc.RangeSlider,
    dcc.Checklist,
    dcc.RadioItems,
    dcc.Input,
    dcc.Textarea,
    dbc.Checklist,
    dbc.RadioItems,
    dbc.Checkbox,
    dbc.Switch,
    dmc.DatePickerInput,
)

_MULTI_PROP_COMPONENTS = (dcc.DatePickerRange,)
_TRACKED_CLASS_NAMES = {
    "Dropdown",
    "Slider",
    "RangeSlider",
    "Checklist",
    "RadioItems",
    "Input",
    "Textarea",
    "DatePickerInput",
    "DatePickerRange",
    "Checkbox",
    "Switch",
}
_EXCLUDED_IDS = {"theme-selector"}
_EXCLUDED_ID_PREFIXES = (
    "_pages",
    "__on_page_load_action",
    "saved-views",
    "vizro",
    "collapse-",
    "nav-",
)


@dataclass
class _TrackedProp:
    component_id: Any
    prop: str
    store_key: str
    store_subkey: str | None = None
    browser_paths: set[str] = field(default_factory=set)


def register_saved_views(dash_app) -> None:
    """Attach saved-view layout and callbacks to a built Dash/Vizro app."""
    tracked_props = _collect_tracked_props(dash_app)
    _append_shell(dash_app)
    _register_callbacks(dash_app, tracked_props)
    logger.info("Extension enabled: saved_views controls=%d", len(tracked_props))


def _collect_tracked_props(dash_app) -> list[_TrackedProp]:
    by_output: dict[tuple[str, str], _TrackedProp] = {}

    def add_tracked(component_id: Any, prop: str, subkey: str | None = None) -> None:
        id_text = _component_id_key(component_id)
        if _is_excluded_id(id_text):
            return
        by_output.setdefault(
            (id_text, prop),
            _TrackedProp(
                component_id=component_id,
                prop=prop,
                store_key=id_text,
                store_subkey=subkey,
            ),
        )

    def add_layout(root: Any) -> None:
        for component in _walk_components(root):
            if not _is_trackable(component):
                continue
            for prop, subkey in _component_props(component):
                add_tracked(component.id, prop, subkey)

    # Root app.layout is safe to inspect. Vizro page layout partials are not:
    # calling them here can register page callbacks a second time, which makes
    # Dash's front-end duplicate-output validator reject the whole app.
    add_layout(_resolve_layout(dash_app.layout))
    for dependency in _callback_value_dependencies(dash_app):
        add_tracked(
            dependency["id"],
            dependency["property"],
            _store_subkey_for_prop(dependency["property"]),
        )

    return list(by_output.values())


def _callback_value_dependencies(dash_app):
    callback_maps = [
        getattr(dash_app, "callback_map", {}),
        getattr(dash_callback, "GLOBAL_CALLBACK_MAP", {}),
    ]
    for callback_map in callback_maps:
        for callback in callback_map.values():
            yield from _value_dependencies_from_callback(callback)


def _value_dependencies_from_callback(callback: dict[str, Any]):
        for dependency in callback.get("inputs", []) + callback.get("state", []):
            prop = dependency.get("property")
            component_id = dependency.get("id")
            if prop not in {"value", "start_date", "end_date"}:
                continue
            if isinstance(component_id, str) and component_id.startswith("{"):
                continue
            yield dependency


def _store_subkey_for_prop(prop: str) -> str | None:
    return prop if prop in {"start_date", "end_date"} else None


def _resolve_layout(layout: Any) -> Any:
    if callable(layout) and not isinstance(layout, Component):
        try:
            return layout()
        except TypeError:
            return layout
    return layout


def _walk_components(node: Any):
    node = _resolve_layout(node)
    if isinstance(node, Component):
        yield node
        children = getattr(node, "children", None)
        if isinstance(children, (list, tuple)):
            for child in children:
                yield from _walk_components(child)
        elif children is not None:
            yield from _walk_components(children)
    elif isinstance(node, (list, tuple)):
        for child in node:
            yield from _walk_components(child)


def _is_trackable(component: Component) -> bool:
    component_id = getattr(component, "id", None)
    if component_id is None:
        return False
    id_text = _component_id_key(component_id)
    if _is_excluded_id(id_text):
        return False
    if isinstance(component, _MULTI_PROP_COMPONENTS):
        return True
    if isinstance(component, _SINGLE_VALUE_COMPONENTS):
        return True
    return type(component).__name__ in _TRACKED_CLASS_NAMES and hasattr(component, "value")


def _is_excluded_id(id_text: str) -> bool:
    if id_text in _EXCLUDED_IDS:
        return True
    return any(id_text.startswith(prefix) for prefix in _EXCLUDED_ID_PREFIXES)


def _component_props(component: Component) -> list[tuple[str, str | None]]:
    if isinstance(component, dcc.DatePickerRange):
        return [("start_date", "start_date"), ("end_date", "end_date")]
    return [("value", None)]


def _component_id_key(component_id: Any) -> str:
    if isinstance(component_id, dict):
        return json.dumps(component_id, sort_keys=True, separators=(",", ":"))
    return str(component_id)


def _browser_path_candidates(page_path: str, prefix: str) -> set[str]:
    prefix = "/" + prefix.strip("/")
    page_path = page_path or "/"
    candidates = {_store_path(page_path)}
    if page_path == "/":
        candidates.add(_store_path(prefix))
        candidates.add(_store_path(prefix + "/"))
    else:
        candidates.add(_store_path(prefix + page_path))
    return candidates


def _store_path(pathname: str | None) -> str:
    path = (pathname or "/").split("?", 1)[0].split("#", 1)[0] or "/"
    if len(path) > 1:
        path = path.rstrip("/")
    return path


def _matches_path(spec: _TrackedProp, pathname: str | None) -> bool:
    if not spec.browser_paths:
        return True
    return _store_path(pathname) in spec.browser_paths


def _append_shell(dash_app) -> None:
    original_layout = dash_app.layout
    shell = _saved_views_shell()

    if callable(original_layout) and not isinstance(original_layout, Component):
        def wrapped_layout():
            return html.Div([original_layout(), shell])

        dash_app.layout = wrapped_layout
    else:
        dash_app.layout = html.Div([original_layout, shell])


def _saved_views_shell():
    return html.Div(
        [
            dcc.Location(id=LOCATION_ID),
            dcc.Store(id=STORE_ID, storage_type="local"),
            dcc.Download(id=DOWNLOAD_ID),
            html.Div(
                [
                    html.Button(
                        html.Span("tune", className="material-symbols-outlined"),
                        id="na-menu-toggle",
                        className="na-left-dock-button",
                        title="Menu",
                        type="button",
                        **{"aria-label": "Menu"},
                    ),
                    html.Button(
                        html.Span("bookmarks", className="material-symbols-outlined"),
                        id=TOGGLE_ID,
                        className="na-left-dock-button saved-views-toggle",
                        title="Saved views",
                        type="button",
                        n_clicks=0,
                        **{"aria-label": "Saved views"},
                    ),
                ],
                id="na-left-action-dock",
                className="na-left-action-dock",
            ),
            html.Div(
                [
                    html.Div("Saved views", className="na-sidebar-panel-header"),
                    html.Div(
                        [
                            dcc.Input(
                                id=SAVE_NAME_ID,
                                type="text",
                                placeholder="View name",
                                className="saved-views-name-input",
                                debounce=True,
                            ),
                            dbc.Button(
                                [html.Span("save", className="material-symbols-outlined"), html.Span("Save")],
                                id=SAVE_BUTTON_ID,
                                className="saved-views-save-button",
                                color="primary",
                                n_clicks=0,
                            ),
                        ],
                        className="saved-views-save-row",
                    ),
                    html.Div(id=STATUS_ID, className="saved-views-status"),
                    html.H3("Current page", className="saved-views-section-title"),
                    html.Div(id=LIST_ID, className="saved-views-list"),
                ],
                id=PANEL_ID,
                className="na-sidebar-panel saved-views-panel na-sidebar-panel-hidden",
            ),
        ],
        id="saved-views-root",
    )


def _register_callbacks(dash_app, tracked_props: list[_TrackedProp]) -> None:
    value_states = [
        State(spec.component_id, spec.prop, allow_optional=True)
        for spec in tracked_props
    ]

    @dash_app.callback(
        Output(LIST_ID, "children"),
        Input(STORE_ID, "data"),
        Input(LOCATION_ID, "pathname"),
    )
    def _render_saved_views(store, pathname):
        page_views = (store or {}).get(_store_path(pathname), {})
        if not page_views:
            return html.Div("No saved views for this page yet.", className="saved-views-empty")
        return [
            _saved_view_item(name)
            for name in sorted(page_views, key=str.casefold)
        ]

    @dash_app.callback(
        Output(STORE_ID, "data"),
        Output(SAVE_NAME_ID, "value"),
        Output(STATUS_ID, "children"),
        Input(SAVE_BUTTON_ID, "n_clicks"),
        Input({"type": DELETE_BUTTON_TYPE, "name": ALL}, "n_clicks"),
        Input({"type": RENAME_BUTTON_TYPE, "name": ALL}, "n_clicks"),
        State(LOCATION_ID, "pathname"),
        State(STORE_ID, "data"),
        State(SAVE_NAME_ID, "value"),
        State({"type": RENAME_INPUT_TYPE, "name": ALL}, "value"),
        State({"type": RENAME_INPUT_TYPE, "name": ALL}, "id"),
        *value_states,
        prevent_initial_call=True,
    )
    def _mutate_saved_views(
        _save_clicks,
        _delete_clicks,
        _rename_clicks,
        pathname,
        store,
        save_name,
        rename_values,
        rename_ids,
        *component_values,
    ):
        triggered = ctx.triggered_id
        if not triggered:
            raise PreventUpdate

        data = deepcopy(store or {})
        page_path = _store_path(pathname)
        page_views = data.setdefault(page_path, {})

        if triggered == SAVE_BUTTON_ID:
            name = (save_name or "").strip()
            if not name:
                return no_update, no_update, "Name the view before saving."
            page_views[name] = _view_from_values(pathname, tracked_props, component_values)
            return data, "", f"Saved \"{name}\"."

        if isinstance(triggered, dict) and triggered.get("type") == DELETE_BUTTON_TYPE:
            name = str(triggered.get("name", ""))
            page_views.pop(name, None)
            if not page_views:
                data.pop(page_path, None)
            return data, no_update, f"Deleted \"{name}\"."

        if isinstance(triggered, dict) and triggered.get("type") == RENAME_BUTTON_TYPE:
            old_name = str(triggered.get("name", ""))
            new_name = _rename_value(old_name, rename_values or [], rename_ids or [])
            if not new_name:
                return no_update, no_update, "Enter a new name before renaming."
            if old_name not in page_views:
                return no_update, no_update, "That saved view no longer exists."
            if new_name != old_name and new_name in page_views:
                return no_update, no_update, f"\"{new_name}\" already exists."
            page_views[new_name] = page_views.pop(old_name)
            return data, no_update, f"Renamed \"{old_name}\" to \"{new_name}\"."

        raise PreventUpdate

    if tracked_props:
        @dash_app.callback(
            [Output(spec.component_id, spec.prop, allow_duplicate=True) for spec in tracked_props],
            Input({"type": RESTORE_BUTTON_TYPE, "name": ALL}, "n_clicks"),
            State(LOCATION_ID, "pathname"),
            State(STORE_ID, "data"),
            prevent_initial_call=True,
        )
        def _restore_saved_view(_restore_clicks, pathname, store):
            triggered = ctx.triggered_id
            if not isinstance(triggered, dict):
                raise PreventUpdate
            name = str(triggered.get("name", ""))
            view = (store or {}).get(_store_path(pathname), {}).get(name)
            if not isinstance(view, dict):
                raise PreventUpdate
            return [
                _restore_value(spec, view, pathname)
                for spec in tracked_props
            ]

    @dash_app.callback(
        Output(DOWNLOAD_ID, "data"),
        Input({"type": EXPORT_BUTTON_TYPE, "name": ALL}, "n_clicks"),
        State(LOCATION_ID, "pathname"),
        State(STORE_ID, "data"),
        prevent_initial_call=True,
    )
    def _export_saved_view(_export_clicks, pathname, store):
        triggered = ctx.triggered_id
        if not isinstance(triggered, dict):
            raise PreventUpdate
        name = str(triggered.get("name", ""))
        view = (store or {}).get(_store_path(pathname), {}).get(name)
        if not isinstance(view, dict):
            raise PreventUpdate
        filename = f"saved-view-{_slugify(name)}.json"
        return dcc.send_string(json.dumps(view, indent=2, ensure_ascii=False, default=str), filename)


def _saved_view_item(name: str):
    button_id = {"name": name}
    return html.Div(
        [
            dbc.Button(
                html.Span("play_arrow", className="material-symbols-outlined"),
                id={**button_id, "type": RESTORE_BUTTON_TYPE},
                className="saved-views-icon-button saved-views-restore",
                color="secondary",
                title=f"Restore {name}",
                n_clicks=0,
            ),
            dcc.Input(
                id={**button_id, "type": RENAME_INPUT_TYPE},
                value=name,
                type="text",
                debounce=True,
                className="saved-views-rename-input",
            ),
            dbc.Button(
                html.Span("drive_file_rename_outline", className="material-symbols-outlined"),
                id={**button_id, "type": RENAME_BUTTON_TYPE},
                className="saved-views-icon-button",
                color="secondary",
                title=f"Rename {name}",
                n_clicks=0,
            ),
            dbc.Button(
                html.Span("download", className="material-symbols-outlined"),
                id={**button_id, "type": EXPORT_BUTTON_TYPE},
                className="saved-views-icon-button",
                color="secondary",
                title=f"Export {name}",
                n_clicks=0,
            ),
            dbc.Button(
                html.Span("delete", className="material-symbols-outlined"),
                id={**button_id, "type": DELETE_BUTTON_TYPE},
                className="saved-views-icon-button saved-views-delete",
                color="secondary",
                title=f"Delete {name}",
                n_clicks=0,
            ),
        ],
        className="saved-views-item",
    )


def _view_from_values(
    pathname: str | None,
    tracked_props: list[_TrackedProp],
    component_values: tuple[Any, ...],
) -> dict[str, Any]:
    view: dict[str, Any] = {}
    for spec, value in zip(tracked_props, component_values):
        if not _matches_path(spec, pathname):
            continue
        if spec.store_subkey:
            bucket = view.setdefault(spec.store_key, {})
            if isinstance(bucket, dict):
                bucket[spec.store_subkey] = value
        else:
            view[spec.store_key] = value
    return view


def _restore_value(spec: _TrackedProp, view: dict[str, Any], pathname: str | None):
    if not _matches_path(spec, pathname):
        return no_update
    if spec.store_key not in view:
        return no_update
    value = view[spec.store_key]
    if spec.store_subkey:
        if not isinstance(value, dict) or spec.store_subkey not in value:
            return no_update
        return value[spec.store_subkey]
    return value


def _rename_value(old_name: str, values: list[str], ids: list[dict[str, Any]]) -> str:
    for value, input_id in zip(values, ids):
        if input_id.get("name") == old_name:
            return (value or "").strip()
    return ""


def _slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-")
    return slug or "view"
