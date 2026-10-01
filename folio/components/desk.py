import reflex as rx
from folio.state import ReaderState

def brand() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon("book-open", class_name="h-5 w-5 text-white"),
            class_name="flex h-10 w-10 shrink-0 items-center justify-center rounded-sm bg-[#3C7771]",
        ),
        rx.el.div(
            rx.el.p(
                "Folio",
                class_name="font-['Cormorant_Garamond'] text-[29px] font-semibold leading-none tracking-tight",
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
        rx.el.div(
            brand(),
            class_name=rx.cond(
                ReaderState.is_dark,
                "hidden border-b border-neutral-800 px-6 py-6 lg:block",
                "hidden border-b border-[#D9DDD4] px-6 py-6 lg:block",
            ),
        ),
        rx.el.div(
            rx.upload.root(
                rx.el.div(
                    rx.icon("upload", class_name="mb-2 h-5 w-5 text-[#3C7771]"),
                    rx.el.p("Drop document or browse", class_name="text-xs font-medium"),
                    rx.el.p("PDF · DOCX · EPUB · TXT · MD", class_name="text-[10px] opacity-60 mt-1"),
                    class_name=rx.cond(
                        ReaderState.is_dark,
                        "flex flex-col items-center justify-center p-4 border border-dashed border-neutral-700 rounded-sm bg-neutral-900 cursor-pointer hover:bg-neutral-800 transition-colors",
                        "flex flex-col items-center justify-center p-4 border border-dashed border-[#A9B4AB] rounded-sm bg-[#FCFAF5] cursor-pointer hover:bg-white transition-colors",
                    ),
                ),
                id="documents",
                multiple=True,
            ),
            rx.cond(
                rx.selected_files("documents").length() > 0,
                rx.el.div(
                    rx.foreach(
                        rx.selected_files("documents"),
                        lambda f: rx.el.p(f, class_name="text-[11px] truncate"),
                    ),
                    class_name=rx.cond(
                        ReaderState.is_dark,
                        "mt-2 p-2 bg-neutral-900 border border-neutral-800 rounded max-h-16 overflow-y-auto",
                        "mt-2 p-2 bg-white border border-[#D9DDD4] rounded max-h-16 overflow-y-auto",
                    ),
                ),
            ),
            rx.el.button(
                rx.cond(ReaderState.is_loading, "Adding to shelf...", "Add to shelf"),
                on_click=ReaderState.handle_upload(rx.upload_files(upload_id="documents")),
                disabled=ReaderState.is_loading,
                class_name="mt-2 w-full rounded-sm bg-[#3C7771] py-2 text-xs font-semibold text-white hover:bg-[#2E605C] disabled:opacity-50 cursor-pointer",
            ),
            rx.cond(
                ReaderState.error_message != "",
                rx.el.p(ReaderState.error_message, class_name="mt-1 text-[11px] text-red-500"),
            ),
            class_name=rx.cond(
                ReaderState.is_dark,
                "px-6 py-4 border-b border-neutral-800",
                "px-6 py-4 border-b border-[#D9DDD4]",
            ),
        ),
        rx.el.div(
            rx.el.p("SAVED ON DISK", class_name="text-[10px] font-bold tracking-widest opacity-60 mb-3"),
            rx.foreach(
                ReaderState.documents,
                lambda doc: rx.el.div(
                    rx.el.button(
                        rx.el.p(doc["title"], class_name="truncate text-xs font-semibold text-left"),
                        rx.el.p(f"{doc['format']} · {doc['words']} words", class_name="text-[10px] opacity-60 text-left"),
                        on_click=lambda: ReaderState.select_document(doc["id"]),
                        class_name="flex-1 text-left min-w-0 pr-2",
                    ),
                    rx.el.button(
                        rx.icon("x", class_name="h-3 w-3 text-red-500 hover:text-red-700"),
                        on_click=lambda: ReaderState.remove_document(doc["id"]),
                    ),
                    class_name=rx.cond(
                        ReaderState.active_id == doc["id"],
                        "flex items-center justify-between p-2 mb-1 rounded bg-[#3C7771]/20 border-l-2 border-[#3C7771]",
                        "flex items-center justify-between p-2 mb-1 rounded hover:bg-black/5 dark:hover:bg-white/5",
                    ),
                ),
            ),
            class_name="flex-1 overflow-y-auto px-6 py-4",
        ),
        class_name=rx.cond(
            ReaderState.is_dark,
            "w-64 bg-neutral-900 border-r border-neutral-800 flex flex-col h-screen shrink-0 text-neutral-100",
            "w-64 bg-[#F2F0E8] border-r border-[#D9DDD4] flex flex-col h-screen shrink-0 text-[#1D2A38]",
        ),
    )

def translated_reader_modal() -> rx.Component:
    """Dedicated distraction-free reading window for the translated text."""
    return rx.cond(
        ReaderState.show_reader_window,
        rx.el.div(
            rx.el.div(
                # Modal Header
                rx.el.div(
                    rx.el.div(
                        rx.el.h2(f"{ReaderState.active_document['title']} (Translated)", class_name="text-xl font-bold font-['Cormorant_Garamond']"),
                        rx.el.p(f"Language: {ReaderState.target_language.upper()} · Distraction-free View", class_name="text-xs opacity-60"),
                        class_name="flex flex-col",
                    ),
                    rx.el.div(
                        rx.el.button(
                            rx.icon("download", class_name="h-4 w-4 mr-1"),
                            "Export Translation (.txt)",
                            on_click=ReaderState.export_translation_from_reader,
                            class_name="bg-[#3C7771] hover:bg-[#2E605C] text-white text-xs px-3 py-1.5 rounded flex items-center font-medium cursor-pointer",
                        ),
                        rx.el.button(
                            rx.icon("x", class_name="h-5 w-5"),
                            on_click=ReaderState.toggle_reader_window,
                            class_name="p-1 rounded hover:bg-black/10 dark:hover:bg-white/10",
                        ),
                        class_name="flex items-center gap-3",
                    ),
                    class_name=rx.cond(
                        ReaderState.is_dark,
                        "flex justify-between items-center pb-4 border-b border-neutral-800",
                        "flex justify-between items-center pb-4 border-b border-[#D9DDD4]",
                    ),
                ),
                # Modal Content
                rx.el.div(
                    rx.cond(
                        ReaderState.full_translated_document_text != "",
                        rx.el.div(
                            rx.foreach(
                                ReaderState.visible_translations,
                                lambda t, idx: rx.cond(
                                    t != "",
                                    rx.el.div(
                                        rx.el.div(
                                            rx.el.span(f"Passage {idx + 1}", class_name="text-[10px] font-bold text-[#3C7771]"),
                                            rx.el.button(
                                                rx.icon("volume-2", class_name="h-3.5 w-3.5 text-[#3C7771] hover:scale-110 transition-transform"),
                                                on_click=lambda: ReaderState.speak_text(t),
                                                title="Read passage aloud",
                                            ),
                                            class_name="flex items-center justify-between mb-1",
                                        ),
                                        rx.el.p(t, class_name="leading-relaxed"),
                                        class_name="p-4 mb-4 rounded border border-neutral-200 dark:border-neutral-800 bg-black/[0.02] dark:bg-white/[0.02]",
                                    ),
                                ),
                            ),
                        ),
                        rx.el.p("No translation available yet. Translate the document or page first.", class_name="italic opacity-60 text-center py-12"),
                    ),
                    class_name="flex-1 overflow-y-auto py-6 font-sans",
                    style={"fontSize": f"{ReaderState.font_size}px"},
                ),
                class_name=rx.cond(
                    ReaderState.is_dark,
                    "relative flex flex-col w-full max-w-4xl max-h-[85vh] bg-neutral-900 border border-neutral-800 text-neutral-100 rounded-lg p-6 shadow-2xl",
                    "relative flex flex-col w-full max-w-4xl max-h-[85vh] bg-[#FCFAF5] border border-[#D9DDD4] text-[#1D2A38] rounded-lg p-6 shadow-2xl",
                ),
            ),
            class_name="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4",
        ),
    )

def split_reading_desk() -> rx.Component:
    return rx.el.div(
        # Top Header Bar: Document Title, Light/Dark Toggle, Reader Window Button
        rx.el.div(
            rx.el.div(
                rx.el.h1(ReaderState.active_document["title"], class_name="text-3xl font-['Cormorant_Garamond'] font-semibold"),
                rx.el.span(f"{ReaderState.active_document['words']} words · Page {ReaderState.current_page + 1} of {ReaderState.active_document['pages']}", class_name="text-xs opacity-60"),
                class_name="flex flex-col gap-1",
            ),
            rx.el.div(
                # Clean Light / Dark Toggle
                rx.el.button(
                    rx.cond(ReaderState.is_dark, rx.icon("sun", class_name="h-4 w-4"), rx.icon("moon", class_name="h-4 w-4")),
                    on_click=ReaderState.toggle_theme,
                    class_name=rx.cond(
                        ReaderState.is_dark,
                        "p-2 rounded border border-neutral-700 hover:bg-neutral-800 text-yellow-400 cursor-pointer",
                        "p-2 rounded border border-[#CBD5CA] hover:bg-[#EAE8DF] text-neutral-700 cursor-pointer",
                    ),
                    title="Toggle Theme",
                ),
                # Dedicated Reader Window Button
                rx.el.button(
                    rx.icon("maximize-2", class_name="h-3.5 w-3.5 mr-1.5"),
                    "Reader Window",
                    on_click=ReaderState.toggle_reader_window,
                    class_name="bg-[#3C7771] hover:bg-[#2E605C] text-white text-xs px-3 py-1.5 rounded font-semibold flex items-center cursor-pointer shadow-sm",
                ),
                rx.el.button(
                    "Edit",
                    on_click=ReaderState.open_editor,
                    class_name=rx.cond(
                        ReaderState.is_dark,
                        "text-xs border border-neutral-700 px-3 py-1.5 rounded hover:bg-neutral-800",
                        "text-xs border border-[#CBD5CA] px-3 py-1.5 rounded hover:bg-[#EAE8DF]",
                    ),
                ),
                rx.el.button("A-", on_click=ReaderState.decrease_font, class_name=rx.cond(ReaderState.is_dark, "px-2 py-1 border border-neutral-700 text-xs rounded", "px-2 py-1 border border-[#CBD5CA] text-xs rounded")),
                rx.el.button("A+", on_click=ReaderState.increase_font, class_name=rx.cond(ReaderState.is_dark, "px-2 py-1 border border-neutral-700 text-xs rounded", "px-2 py-1 border border-[#CBD5CA] text-xs rounded")),
                rx.el.button("Spacing", on_click=ReaderState.cycle_spacing, class_name=rx.cond(ReaderState.is_dark, "px-2 py-1 border border-neutral-700 text-xs rounded", "px-2 py-1 border border-[#CBD5CA] text-xs rounded")),
                class_name="flex items-center gap-2",
            ),
            class_name=rx.cond(
                ReaderState.is_dark,
                "flex justify-between items-center pb-4 mb-4 border-b border-neutral-800",
                "flex justify-between items-center pb-4 mb-4 border-b border-[#D9DDD4]",
            ),
        ),

        # Action bar: Target Language & Translation Triggers
        rx.el.div(
            rx.el.div(
                rx.el.span("Translate to:", class_name="text-xs font-bold opacity-60"),
                rx.el.select(
                    rx.foreach(ReaderState.languages, lambda l: rx.el.option(l["name"], value=l["code"])),
                    default_value=ReaderState.target_language,
                    on_change=ReaderState.set_target_language,
                    class_name=rx.cond(
                        ReaderState.is_dark,
                        "text-xs border border-neutral-700 p-1.5 rounded bg-neutral-900 font-medium",
                        "text-xs border border-[#CBD5CA] p-1.5 rounded bg-white font-medium",
                    ),
                ),
                class_name="flex items-center gap-2",
            ),
            rx.el.div(
                rx.el.button(
                    rx.icon("text-select", class_name="h-4 w-4 mr-1"),
                    "Translate Selected Passage",
                    on_click=ReaderState.translate_selected_passage,
                    disabled=ReaderState.translation_loading,
                    class_name=rx.cond(
                        ReaderState.is_dark,
                        "bg-neutral-900 border border-[#3C7771] text-[#4DA097] px-3 py-1.5 text-xs font-semibold rounded hover:bg-neutral-800 flex items-center cursor-pointer disabled:opacity-40",
                        "bg-white border border-[#3C7771] text-[#3C7771] px-3 py-1.5 text-xs font-semibold rounded hover:bg-[#3C7771]/10 flex items-center cursor-pointer disabled:opacity-40",
                    ),
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
            class_name=rx.cond(
                ReaderState.is_dark,
                "flex justify-between items-center p-3 bg-neutral-900 border border-neutral-800 rounded mb-3",
                "flex justify-between items-center p-3 bg-[#FCFAF5] border border-[#CBD5CA] rounded mb-3",
            ),
        ),

        # Live status
        rx.cond(
            ReaderState.translation_loading,
            rx.el.div(
                rx.icon("loader-circle", class_name="h-4 w-4 animate-spin text-[#3C7771]"),
                rx.el.span(ReaderState.translation_status, class_name="text-xs text-[#3C7771] font-medium"),
                class_name="flex items-center gap-2 p-2 bg-[#3C7771]/15 border-l-4 border-[#3C7771] mb-3 rounded-r",
            ),
        ),
        rx.cond(
            (ReaderState.translation_status != "") & (~ReaderState.translation_loading),
            rx.el.div(
                rx.el.p(ReaderState.translation_status, class_name="text-xs font-medium"),
                class_name=rx.cond(
                    ReaderState.is_dark,
                    "p-2 bg-neutral-900 border border-neutral-800 rounded mb-3",
                    "p-2 bg-[#F2F0E8] border border-[#D9DDD4] rounded mb-3",
                ),
            ),
        ),

        # 50/50 Split Reading Container
        rx.el.div(
            # Left: Original Document
            rx.el.div(
                rx.el.h2("ORIGINAL TEXT (CLICK TO SELECT)", class_name="text-[10px] font-bold tracking-widest text-[#3C7771] uppercase mb-4 sticky top-0 py-1 border-b backdrop-blur-sm"),
                rx.foreach(
                    ReaderState.visible_paragraphs,
                    lambda p, idx: rx.el.div(
                        rx.el.span(f"Passage {idx + 1}", class_name="text-[10px] font-bold text-[#3C7771] block mb-1"),
                        rx.el.p(p, class_name="leading-relaxed"),
                        on_click=lambda: ReaderState.select_passage(idx + ReaderState.page_start),
                        class_name=rx.cond(
                            ReaderState.selected_passage == (idx + ReaderState.page_start),
                            rx.cond(
                                ReaderState.is_dark,
                                "p-3 mb-3 bg-neutral-800 border-l-4 border-[#3C7771] shadow-sm rounded cursor-pointer transition-all",
                                "p-3 mb-3 bg-[#E6EFE8] border-l-4 border-[#3C7771] shadow-sm rounded cursor-pointer transition-all",
                            ),
                            rx.cond(
                                ReaderState.is_dark,
                                "p-3 mb-3 bg-neutral-900 border border-neutral-800 rounded hover:border-[#3C7771] transition-all cursor-pointer",
                                "p-3 mb-3 bg-white border border-[#CBD5CA] rounded hover:border-[#3C7771] transition-all cursor-pointer",
                            ),
                        ),
                    ),
                ),
                class_name="flex-1 w-1/2 overflow-y-auto pr-3",
            ),

            # Right: Translation Column with Text-to-Speech (TTS)
            rx.el.div(
                rx.el.h2("TRANSLATION (TARGET)", class_name="text-[10px] font-bold tracking-widest text-[#3C7771] uppercase mb-4 sticky top-0 py-1 border-b backdrop-blur-sm"),
                rx.foreach(
                    ReaderState.visible_translations,
                    lambda t, idx: rx.el.div(
                        rx.el.div(
                            rx.el.span(f"Passage {idx + 1}", class_name="text-[10px] font-bold text-[#3C7771]"),
                            rx.cond(
                                t != "",
                                rx.el.button(
                                    rx.icon("volume-2", class_name="h-4 w-4 text-[#3C7771] hover:scale-110 transition-transform"),
                                    on_click=lambda: ReaderState.speak_text(t),
                                    title="Listen in Malayalam / Target Language",
                                    class_name="cursor-pointer",
                                ),
                            ),
                            class_name="flex items-center justify-between mb-1",
                        ),
                        rx.cond(
                            t != "",
                            rx.el.p(t, class_name="leading-relaxed font-sans"),
                            rx.el.p("Click 'Translate' above to generate...", class_name="text-xs italic opacity-60"),
                        ),
                        class_name=rx.cond(
                            ReaderState.selected_passage == (idx + ReaderState.page_start),
                            rx.cond(
                                ReaderState.is_dark,
                                "p-3 mb-3 bg-neutral-800 border-l-4 border-[#3C7771] shadow-sm rounded",
                                "p-3 mb-3 bg-[#E6EFE8] border-l-4 border-[#3C7771] shadow-sm rounded",
                            ),
                            rx.cond(
                                ReaderState.is_dark,
                                "p-3 mb-3 bg-neutral-900 border border-neutral-800 rounded",
                                "p-3 mb-3 bg-[#FCFAF5] border border-[#CBD5CA] rounded",
                            ),
                        ),
                    ),
                ),
                class_name=rx.cond(
                    ReaderState.is_dark,
                    "flex-1 w-1/2 overflow-y-auto pl-3 border-l border-neutral-800",
                    "flex-1 w-1/2 overflow-y-auto pl-3 border-l border-[#D9DDD4]",
                ),
            ),
            class_name=rx.cond(
                ReaderState.is_dark,
                "flex flex-1 min-h-[500px] border border-neutral-800 rounded p-4 bg-neutral-950",
                "flex flex-1 min-h-[500px] border border-[#D9DDD4] rounded p-4 bg-[#F7F4EC]",
            ),
            style={"fontSize": f"{ReaderState.font_size}px"},
        ),

        # Pagination Footer
        rx.el.div(
            rx.el.button(
                "Previous Page",
                on_click=lambda: ReaderState.change_page(-1),
                disabled=ReaderState.current_page <= 0,
                class_name=rx.cond(
                    ReaderState.is_dark,
                    "border border-neutral-700 px-4 py-2 text-xs font-semibold rounded bg-neutral-900 disabled:opacity-40 cursor-pointer",
                    "border border-[#CBD5CA] px-4 py-2 text-xs font-semibold rounded bg-white disabled:opacity-40 cursor-pointer",
                ),
            ),
            rx.el.span(f"Page {ReaderState.current_page + 1} of {ReaderState.active_document['pages']}", class_name="text-xs opacity-60"),
            rx.el.button(
                "Next Page",
                on_click=lambda: ReaderState.change_page(1),
                disabled=ReaderState.current_page + 1 >= ReaderState.active_document["pages"],
                class_name=rx.cond(
                    ReaderState.is_dark,
                    "border border-neutral-700 px-4 py-2 text-xs font-semibold rounded bg-neutral-900 disabled:opacity-40 cursor-pointer",
                    "border border-[#CBD5CA] px-4 py-2 text-xs font-semibold rounded bg-white disabled:opacity-40 cursor-pointer",
                ),
            ),
            class_name=rx.cond(
                ReaderState.is_dark,
                "flex justify-between items-center mt-4 pt-3 border-t border-neutral-800",
                "flex justify-between items-center mt-4 pt-3 border-t border-[#D9DDD4]",
            ),
        ),
        translated_reader_modal(),
        class_name=rx.cond(
            ReaderState.is_dark,
            "flex flex-col flex-1 h-screen overflow-y-auto px-8 py-6 bg-neutral-950 text-neutral-100",
            "flex flex-col flex-1 h-screen overflow-y-auto px-8 py-6 bg-[#F7F4EC] text-[#1D2A38]",
        ),
    )

def reading_desk() -> rx.Component:
    return rx.el.div(
        shelf(),
        rx.cond(
            ReaderState.active_id != "",
            split_reading_desk(),
            rx.el.div("Upload or select a document from the left shelf to begin reading.", class_name="p-16 opacity-60 flex-1"),
        ),
        class_name=rx.cond(
            ReaderState.is_dark,
            "flex h-screen w-screen overflow-hidden bg-neutral-950 font-['DM_Sans']",
            "flex h-screen w-screen overflow-hidden bg-[#F7F4EC] font-['DM_Sans']",
        ),
    )

def edit_workspace() -> rx.Component:
    return rx.el.div(
        rx.el.form(
            rx.el.div(
                rx.el.h2("The Writing Desk", class_name="font-['Cormorant_Garamond'] text-3xl font-semibold"),
                rx.el.button("Back to Reader", on_click=rx.redirect("/"), type="button", class_name="text-xs border px-3 py-1.5 rounded"),
                class_name="flex items-center justify-between mb-4",
            ),
            rx.el.input(name="title", default_value=ReaderState.editor_title, class_name="w-full text-xl font-bold p-3 border rounded mb-4 font-['Cormorant_Garamond'] bg-transparent"),
            rx.el.textarea(name="text", default_value=ReaderState.editor_text, class_name="w-full h-[60vh] p-4 border rounded font-['Cormorant_Garamond'] text-lg leading-relaxed mb-4 bg-transparent"),
            rx.el.button("Save changes", type="submit", class_name="bg-[#3C7771] text-white px-5 py-2.5 rounded text-xs font-semibold hover:bg-[#2E605C] cursor-pointer"),
            on_submit=ReaderState.save_edit,
            class_name="max-w-4xl mx-auto p-8",
        ),
        class_name=rx.cond(
            ReaderState.is_dark,
            "h-screen w-screen bg-neutral-950 text-neutral-100 overflow-y-auto font-['DM_Sans']",
            "h-screen w-screen bg-[#F7F4EC] text-[#1D2A38] overflow-y-auto font-['DM_Sans']",
        ),
    )