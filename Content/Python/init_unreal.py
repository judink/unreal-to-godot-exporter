"""
Unreal To Godot Exporter - Plugin Entry Point

This file runs automatically when the Unreal Editor starts (if the plugin is enabled).
It registers the editor menus and toolbar buttons for the Godot exporter.
"""

import unreal

_initialized = False


def _on_editor_ready(delta_time):
    """
    Called on the first Slate tick after editor startup.
    Registers menus then removes itself from the tick callback.
    """
    global _initialized
    if _initialized:
        return
    _initialized = True

    try:
        from unreal_to_godot import menu
        menu.register_menus()
        unreal.log("UnrealToGodotExporter: Plugin loaded successfully.")
        unreal.log("UnrealToGodotExporter: Use Tools > 'Export to Godot' or right-click assets in Content Browser.")
    except Exception as e:
        unreal.log_error(f"UnrealToGodotExporter: Failed to initialize - {e}")

    # Unregister this tick callback after first run
    unreal.unregister_slate_post_tick_callback(_tick_handle)


# Register a one-shot post-tick callback to initialize after editor is ready
_tick_handle = unreal.register_slate_post_tick_callback(_on_editor_ready)
