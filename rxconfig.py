import reflex as rx

config = rx.Config(
    app_name="folio",
    reflex_badge="bottom-left",  
    plugins=[
        rx.plugins.TailwindV4Plugin(),
    ],
)