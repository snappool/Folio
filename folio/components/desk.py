import reflex as rx
from folio.state import ReaderState, DocumentData

def brand() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon("book-open", class_name="h-5 w-5 text-[#F7F4EC]"),
            class_name="flex h-10 w-10 shrink-0 items-center justify-center rounded-sm bg-[#1D2A38]",
        ),
        rx.el.div(
            rx.el.p(
                "Folio",
                class_name="font-['Cormorant_Garamond'] text-[29px] font-semibold leading-none tracking-tight text-[#1D2A38]",
            ),
            rx.el.p(
                "A QUIET PLACE TO READ",
                class_name="mt-1 text-[9px] font-bold tracking-[0.19em] text-[#3C7771]",
            ),
        ),
        class_name="flex items-center gap-3",
    )

def shelf() -> rx.Component:
    return rx.el.aside(
        rx.el.div(brand(), class_name="hidden border-b border-[#D9DDD4] px-6 py-6 lg:block"),
        rx.el.div(
            rx.upload.root(
                rx.el.div(
                    rx.icon("upload", class_name="mb-2 h-5 w-5 text-[#3C7771]"),
                    rx.el.p("Drop document or browse", class_name="text-xs text-[#5D6B70]"),
                    class_name="flex flex-col items-center justify-center p-4 border border-dashed border-[#A9B4AB] rounded-sm bg-[#FCFAF5] cursor-pointer",
                ),
                id="documents",
                multiple=True,
            ),
            rx.el.button(
                "Add to shelf",
                on_click=ReaderState.handle_upload(rx.upload_files(upload_id="documents")),
                class_name="mt-2 w-full rounded-sm bg-[#3C7771] py-2 text-xs font-semibold text-white hover:bg-[#2E605C]",
            ),
            class_name="px-6 py-4 border-b border-[#D9DDD4]",
        ),
        rx.el.div(
            rx.el.p("SAVED ON DISK", class_name="text-[10px] font-bold tracking-widest text-[#667875] mb-3"),
            rx.foreach(
                ReaderState.documents,
                lambda doc: rx.el.div(
                    rx.el.button(
                        rx.el.p(doc["title"], class_name="truncate text-xs font-semibold text-[#1D2A38]"),
                        rx.el.p(f"{doc['format']} · {doc['words']} words", class_name="text-[10px] text-[#64716D]"),
                        on_click=lambda: ReaderState.select_document(doc["id"]),
                        class_name="flex-1 text-left",
                    ),
                    rx.el.button(
                        rx.icon("x", class_name="h-3 w-3 text-red-600"),
                        on_click=lambda: ReaderState.remove_document(doc["id"]),
                    ),
                    class_name=rx.cond(
                        ReaderState.active_id == doc["id"],
                        "flex items-center justify-between p-2 mb-1 rounded bg-[#EDF3EE] border-l-2 border-[#3C7771]",
                        "flex items-center justify-between p-2 mb-1 rounded hover:bg-[#EAE8DF]",
                    ),
                ),
            ),
            class_name="flex-1 overflow-y-auto px-6 py-4",
        ),
        class_name="w-64 bg-[#F2F0E8] border-r border-[#D9DDD4] flex flex-col h-screen shrink-0",
    )

def split_reading_desk() -> rx.Component:
    return rx.el.div(
        # Top Header Bar
        rx.el.div(
            rx.el.div(
                rx.el.h1(ReaderState.active_document["title"], class_name="text-3xl font-['Cormorant_Garamond'] font-semibold text-[#1D2A38]"),
                rx.el.span(f"{ReaderState.active_document['words']} words · Page {ReaderState.current_page + 1} of {ReaderState.active_document['pages']}", class_name="text-xs text-[#64716D]"),
                class_name="flex flex-col gap-1",
            ),
            rx.el.div(
                rx.el.button("Edit Text", on_click=ReaderState.open_editor, class_name="text-xs border border-[#3C7771] px-3 py-1.5 rounded text-[#3C7771] hover:bg-[#EAF1EB]"),
                rx.el.button("A-", on_click=ReaderState.decrease_font, class_name="px-2 py-1 border text-xs"),
                rx.el.button("A+", on_click=ReaderState.increase_font, class_name="px-2 py-1 border text-xs"),
                rx.el.button("Spacing", on_click=ReaderState.cycle_spacing, class_name="px-2 py-1 border text-xs"),
                class_name="flex items-center gap-2",
            ),
            class_name="flex justify-between items-center pb-4 mb-4 border-b border-[#D9DDD4]",
        ),

        # Translation Controls Bar
        rx.el.div(
            rx.el.div(
                rx.el.span("Translate to:", class_name="text-xs font-bold text-[#64716D]"),
                rx.el.select(
                    rx.foreach(ReaderState.languages, lambda l: rx.el.option(l["name"], value=l["code"])),
                    default_value=ReaderState.target_language,
                    on_change=ReaderState.set_target_language,
                    class_name="text-xs border border-[#CBD5CA] p-1.5 rounded bg-white font-medium",
                ),
                class_name="flex items-center gap-2",
            ),
            rx.el.div(
                rx.el.button(
                    rx.icon("text-select", class_name="h-4 w-4 mr-1"),
                    "Translate Selected Passage",
                    on_click=ReaderState.translate_selected_passage,
                    disabled=ReaderState.translation_loading,
                    class_name="bg-white border border-[#3C7771] text-[#3C7771] px-3 py-1.5 text-xs font-semibold rounded hover:bg-[#EDF3EE] flex items-center cursor-pointer disabled:opacity-40",
                ),
                rx.el.button(
                    rx.icon("book-open", class_name="h-4 w-4 mr-1"),
                    "Translate This Page",
                    on_click=ReaderState.translate_entire_page,
                    disabled=ReaderState.translation_loading,
                    class_name="bg-[#3C7771] text-white px-3 py-1.5 text-xs font-semibold rounded hover:bg-[#2E605C] flex items-center cursor-pointer disabled:opacity-40",
                ),
                class_name="flex items-center gap-3",
            ),
            class_name="flex justify-between items-center p-3 bg-[#FCFAF5] border border-[#CBD5CA] rounded mb-3",
        ),

        # Live Status & Progress Notice
        rx.cond(
            ReaderState.translation_loading,
            rx.el.div(
                rx.icon("loader-circle", class_name="h-4 w-4 animate-spin text-[#3C7771]"),
                rx.el.span(ReaderState.translation_status, class_name="text-xs text-[#315F5A] font-medium"),
                class_name="flex items-center gap-2 p-2 bg-[#EAF1EB] border-l-4 border-[#3C7771] mb-3",
            ),
        ),
        rx.cond(
            (ReaderState.translation_status != "") & (~ReaderState.translation_loading),
            rx.el.div(
                rx.el.p(ReaderState.translation_status, class_name="text-xs text-[#1D2A38] font-medium"),
                class_name="p-2 bg-[#F2F0E8] border border-[#D9DDD4] rounded mb-3",
            ),
        ),

        # 50/50 Split Reading Container
        rx.el.div(
            # Left Column: Original Text
            rx.el.div(
                rx.el.div(
                    rx.el.h2("ORIGINAL TEXT (CLICK PASSAGE TO SELECT)", class_name="text-[10px] font-bold tracking-widest text-[#3C7771] uppercase mb-4 sticky top-0 bg-[#F7F4EC] py-1 border-b"),
                    rx.foreach(
                        ReaderState.visible_paragraphs,
                        lambda p, idx: rx.el.div(
                            rx.el.span(f"Passage {idx + 1}", class_name="text-[10px] font-bold text-[#3C7771] block mb-1"),
                            rx.el.p(p, class_name="leading-relaxed"),
                            on_click=lambda: ReaderState.select_passage(idx + ReaderState.page_start),
                            class_name=rx.cond(
                                ReaderState.selected_passage == (idx + ReaderState.page_start),
                                "p-3 mb-3 bg-[#EDF3EE] border-l-4 border-[#3C7771] rounded cursor-pointer shadow-sm transition-all",
                                "p-3 mb-3 bg-white border border-[#E0E5DC] rounded cursor-pointer hover:border-[#3C7771] transition-all",
                            ),
                        ),
                    ),
                ),
                class_name="flex-1 w-1/2 overflow-y-auto pr-3",
            ),

            # Right Column: Translation Text
            rx.el.div(
                rx.el.div(
                    rx.el.h2("TRANSLATION (MALAYALAM / TARGET)", class_name="text-[10px] font-bold tracking-widest text-[#3C7771] uppercase mb-4 sticky top-0 bg-[#F7F4EC] py-1 border-b"),
                    rx.foreach(
                        ReaderState.visible_translations,
                        lambda t, idx: rx.el.div(
                            rx.el.span(f"Passage {idx + 1}", class_name="text-[10px] font-bold text-[#3C7771] block mb-1"),
                            rx.cond(
                                t != "",
                                rx.el.p(t, class_name="leading-relaxed text-[#1D2A38]"),
                                rx.el.p("Click 'Translate' above to generate...", class_name="text-xs italic text-[#8A968F]"),
                            ),
                            class_name="p-3 mb-3 bg-[#FCFAF5] border border-[#E0E5DC] rounded",
                        ),
                    ),
                ),
                class_name="flex-1 w-1/2 overflow-y-auto pl-3 border-l border-[#D9DDD4]",
            ),
            class_name="flex flex-1 min-h-[500px] border border-[#D9DDD4] rounded bg-[#F7F4EC] p-4",
            style={"font-size": f"{ReaderState.font_size}px"},
        ),

        # Pagination Footer
        rx.el.div(
            rx.el.button(
                "Previous Page",
                on_click=lambda: ReaderState.change_page(-1),
                disabled=ReaderState.current_page <= 0,
                class_name="border border-[#CBD5CA] px-4 py-2 text-xs font-semibold rounded bg-white disabled:opacity-40 cursor-pointer",
            ),
            rx.el.span(f"Page {ReaderState.current_page + 1} of {ReaderState.active_document['pages']}", class_name="text-xs text-[#64716D]"),
            rx.el.button(
                "Next Page",
                on_click=lambda: ReaderState.change_page(1),
                disabled=ReaderState.current_page + 1 >= ReaderState.active_document["pages"],
                class_name="border border-[#CBD5CA] px-4 py-2 text-xs font-semibold rounded bg-white disabled:opacity-40 cursor-pointer",
            ),
            class_name="flex justify-between items-center mt-4 pt-3 border-t border-[#D9DDD4]",
        ),
        class_name="flex flex-col flex-1 h-screen overflow-y-auto px-8 py-6",
    )

def reading_desk() -> rx.Component:
    return rx.el.div(
        shelf(),
        rx.cond(
            ReaderState.active_id != "",
            split_reading_desk(),
            rx.el.div("Upload or select a document from the left shelf to begin reading.", class_name="p-16 text-[#64716D] flex-1"),
        ),
        class_name="flex h-screen w-screen overflow-hidden bg-[#F7F4EC] font-['DM_Sans']",
    )

def edit_workspace() -> rx.Component:
    return rx.el.div(
        rx.el.form(
            rx.el.div(
                rx.el.h2("The Writing Desk", class_name="font-['Cormorant_Garamond'] text-3xl font-semibold text-[#1D2A38]"),
                rx.el.button("Back to Reader", on_click=rx.redirect("/"), type="button", class_name="text-xs border border-[#CBD5CA] px-3 py-1.5 rounded"),
                class_name="flex items-center justify-between mb-4",
            ),
            rx.el.input(name="title", default_value=ReaderState.editor_title, class_name="w-full text-xl font-bold p-3 border border-[#D4DBD0] rounded mb-4 font-['Cormorant_Garamond'] bg-[#FCFAF5]"),
            rx.el.textarea(name="text", default_value=ReaderState.editor_text, class_name="w-full h-[60vh] p-4 border border-[#D4DBD0] rounded font-['Cormorant_Garamond'] text-lg leading-relaxed mb-4 bg-[#FCFAF5]"),
            rx.el.button("Save changes", type="submit", class_name="bg-[#3C7771] text-white px-5 py-2.5 rounded text-xs font-semibold hover:bg-[#2E605C]"),
            on_submit=ReaderState.save_edit,
            class_name="max-w-4xl mx-auto p-8",
        ),
        class_name="h-screen w-screen bg-[#F7F4EC] overflow-y-auto font-['DM_Sans']",
    )