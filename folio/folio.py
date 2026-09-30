import reflex as rx
from folio.components.desk import shelf, reading_desk, edit_workspace
from folio.state import ReaderState

def index() -> rx.Component:
    return rx.el.div(
        reading_desk(),
        on_mount=ReaderState.load_library,
    )

def edit_page() -> rx.Component:
    return rx.el.div(
        edit_workspace(),
        on_mount=ReaderState.load_library,
    )

app = rx.App(
    theme=rx.theme(appearance="light"),
    head_components=[
        rx.el.link(rel="preconnect", href="https://fonts.googleapis.com"),
        rx.el.link(
            rel="preconnect", href="https://fonts.gstatic.com", cross_origin=""
        ),
        rx.el.link(
            href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,400&family=DM+Sans:wght@400;500;600;700&display=swap",
            rel="stylesheet",
        ),
    ],
)

app.add_page(index, route="/")
app.add_page(edit_page, route="/edit")