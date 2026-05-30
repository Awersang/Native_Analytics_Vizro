"""
Native Analytics Vizro - Main Application Entry Point
"""

import vizro.plotly.express as px
from vizro import Vizro
import vizro.models as vm

df = px.data.iris()

page = vm.Page(
    title="Native Analytics - Iris Explorer",
    components=[
        vm.Graph(
            figure=px.scatter(
                df,
                x="sepal_width",
                y="sepal_length",
                color="species",
                title="Iris: Sepal Width vs Length",
            )
        ),
        vm.Graph(
            figure=px.histogram(
                df,
                x="sepal_length",
                color="species",
                title="Iris: Sepal Length Distribution",
            )
        ),
    ],
    controls=[
        vm.Filter(column="species"),
    ],
)

dashboard = vm.Dashboard(pages=[page])

if __name__ == "__main__":
    Vizro().build(dashboard).run()
