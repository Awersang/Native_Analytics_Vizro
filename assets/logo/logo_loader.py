"""
logo_loader.py
──────────────
Drop this file anywhere in your project and import logo_loader_component.
Also drop logo_loader.css into your assets/ folder.

Example usage in a Vizro/Dash layout:

    import vizro.models as vm
    from dash import html
    from logo_loader import logo_loader_component

    page = vm.Page(
        title="My Page",
        components=[
            vm.Graph(id="my-chart", figure=my_fig),
        ],
    )

To use as the page-level loading overlay, wrap any component:

    html.Div([
        logo_loader_component,
        dcc.Loading(
            children=html.Div(id="content"),
            custom_spinner=logo_loader_component,
        )
    ])

Or inject it directly into a layout as a visible element during load.
"""

from dash import html


def make_svg(view_box, path_d, width, height):
    """Return a minimal SVG element with a single white path."""
    return html.Svg(
        viewBox=view_box,
        xmlns="http://www.w3.org/2000/svg",
        style={"display": "block", "width": f"{width}px", "height": f"{height}px"},
        children=[
            html.Path(d=path_d, fill="white"),
        ],
    )


# ── The three shape SVGs ──────────────────────────────────────────────────────

# Shape 1: arch — dome top, straight sides, flat bottom
_shape1_svg = make_svg(
    view_box="0 0 92 162",
    path_d="M0,162 L0,46 A46,46 0 0,1 92,46 L92,162 Z",
    width=92,
    height=162,
)

# Shape 2: U-bowl — flat top, straight sides, dome bottom
_shape2_svg = make_svg(
    view_box="0 0 92 162",
    path_d="M0,0 L92,0 L92,116 A46,46 0 0,1 0,116 Z",
    width=92,
    height=162,
)

# Shape 3: semicircle — dome up, flat bottom
_shape3_svg = make_svg(
    view_box="0 0 92 46",
    path_d="M0,46 A46,46 0 0,1 92,46 Z",
    width=92,
    height=46,
)

# ── Assembled component ───────────────────────────────────────────────────────

logo_loader_component = html.Div(
    className="logo-group",
    children=[
        html.Div(
            className="logo",
            children=[
                html.Div(className="logo-s1-wrap", children=[_shape1_svg]),
                html.Div(className="logo-s2-wrap", children=[_shape2_svg]),
                html.Div(className="logo-s3-wrap", children=[_shape3_svg]),
            ],
        )
    ],
)
