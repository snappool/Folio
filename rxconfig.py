import reflex as rx

config = rx.Config(
    app_name="folio",
    reflex_badge=False,
    plugins=[
        rx.plugins.TailwindV4Plugin(),
    ],
)