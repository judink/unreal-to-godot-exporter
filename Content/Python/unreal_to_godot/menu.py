"""
Editor menu registration for the Unreal-to-Godot Exporter.

Adds menu entries to:
1. Level Editor main menu bar ("Godot Exporter" under Tools)
2. Content Browser right-click context menu ("Export to Godot")
"""

import unreal

_menus_registered = False


def register_menus():
    """Register all editor menus. Called once on editor startup."""
    global _menus_registered
    if _menus_registered:
        return
    _menus_registered = True

    # Unregister the post-tick callback since we only need to run once
    _register_main_menu()
    _register_content_browser_menu()

    menus = unreal.ToolMenus.get()
    menus.refresh_all_widgets()

    unreal.log("UnrealToGodot: Editor menus registered.")


def _register_main_menu():
    """Add 'Godot Exporter' entry under the Tools menu in the Level Editor."""
    menus = unreal.ToolMenus.get()
    main_menu = menus.find_menu("LevelEditor.MainMenu")
    if not main_menu:
        unreal.log_warning("UnrealToGodot: Could not find LevelEditor.MainMenu")
        return

    # Add to the existing Tools menu
    tools_menu = menus.find_menu("LevelEditor.MainMenu.Tools")
    if not tools_menu:
        unreal.log_warning("UnrealToGodot: Could not find Tools menu")
        return

    # Create menu entry
    entry = unreal.ToolMenuEntry(
        name="UnrealToGodot.ExportSelected",
        type=unreal.MultiBlockType.MENU_ENTRY,
        insert_position=unreal.ToolMenuInsert("", unreal.ToolMenuInsertType.FIRST),
    )
    entry.set_label("Export to Godot (Selected Assets)")
    entry.set_tool_tip("Export selected Content Browser assets to Godot via glTF")
    entry.set_string_command(
        unreal.ToolMenuStringCommandType.PYTHON,
        custom_type="",
        string="from unreal_to_godot.ui import show_export_dialog; show_export_dialog()",
    )

    tools_menu.add_menu_entry("GodotExporter", entry)


def _register_content_browser_menu():
    """Add 'Export to Godot' to the Content Browser asset context menu."""
    menus = unreal.ToolMenus.get()

    # Content Browser asset context menu
    cb_menu = menus.find_menu("ContentBrowser.AssetContextMenu")
    if not cb_menu:
        unreal.log_warning(
            "UnrealToGodot: Could not find ContentBrowser.AssetContextMenu"
        )
        return

    entry = unreal.ToolMenuEntry(
        name="UnrealToGodot.CBExport",
        type=unreal.MultiBlockType.MENU_ENTRY,
        insert_position=unreal.ToolMenuInsert("", unreal.ToolMenuInsertType.FIRST),
    )
    entry.set_label("Export to Godot")
    entry.set_tool_tip("Export this asset and its dependencies to Godot via glTF")
    entry.set_string_command(
        unreal.ToolMenuStringCommandType.PYTHON,
        custom_type="",
        string="from unreal_to_godot.ui import show_export_dialog; show_export_dialog()",
    )

    cb_menu.add_menu_entry("GodotExporter", entry)
