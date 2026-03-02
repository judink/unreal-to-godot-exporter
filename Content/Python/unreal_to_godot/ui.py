"""
Export dialog UI for the Unreal-to-Godot Exporter.

Provides a dialog window where users can:
- Review selected assets and their dependencies
- Choose output directory
- Configure export options (format, material baking, etc.)
- Execute the export
"""

import os
import unreal

from unreal_to_godot.config import ExportConfig, FORMAT_GLTF, FORMAT_GLB
from unreal_to_godot.exporter import GodotExporter
from unreal_to_godot.dependency_resolver import DependencyResolver


def show_export_dialog():
    """
    Show the export dialog. Uses Unreal's built-in dialogs since
    pure Python plugins cannot create custom Slate/UMG windows easily.

    Workflow:
    1. Get selected assets from Content Browser
    2. Show asset summary with output path and ask for confirmation
    3. Run export
    """
    # Get selected assets
    selected_assets = unreal.EditorUtilityLibrary.get_selected_assets()
    if not selected_assets or len(selected_assets) == 0:
        unreal.EditorDialog.show_message(
            "Unreal To Godot Exporter",
            "No assets selected.\n\n"
            "Please select assets in the Content Browser first:\n"
            "- Static Mesh\n"
            "- Skeletal Mesh\n"
            "- Animation Sequence",
            unreal.AppMsgType.OK,
        )
        return

    # Determine output directory
    output_dir = _get_output_directory()

    # Categorize and summarize selected assets
    summary = _build_asset_summary(list(selected_assets))

    # Show confirmation dialog with asset summary and output path
    confirm_msg = (
        f"Ready to export {len(selected_assets)} asset(s) to Godot:\n\n"
        f"{summary}\n\n"
        f"Output directory:\n{output_dir}\n\n"
        "The exporter will:\n"
        "- Convert to glTF 2.0 format (Godot compatible)\n"
        "- Include materials and textures automatically\n"
        "- Include skeletons for skeletal meshes/animations\n"
        "- Organize output by asset type\n\n"
        "Continue?"
    )

    result = unreal.EditorDialog.show_message(
        "Unreal To Godot Exporter",
        confirm_msg,
        unreal.AppMsgType.YES_NO,
    )

    if result != unreal.AppReturnType.YES:
        return

    # Configure and run export
    config = ExportConfig()
    config.output_directory = output_dir
    config.output_format = FORMAT_GLB
    config.overwrite_existing = True
    config.organize_by_type = True
    config.generate_manifest = True

    try:
        exporter = GodotExporter(config)
        report = exporter.export_assets(list(selected_assets), output_dir)

        # Show result dialog
        _show_result_dialog(report, output_dir)
    except Exception as e:
        unreal.log_error(f"UnrealToGodot: Export failed - {e}")
        unreal.EditorDialog.show_message(
            "Export Failed",
            f"An error occurred during export:\n\n{e}",
            unreal.AppMsgType.OK,
        )


def _build_asset_summary(assets):
    """Build a human-readable summary of selected assets."""
    static_meshes = []
    skeletal_meshes = []
    animations = []
    unsupported = []

    for asset in assets:
        name = asset.get_name()
        if isinstance(asset, unreal.StaticMesh):
            static_meshes.append(name)
        elif isinstance(asset, unreal.SkeletalMesh):
            skeletal_meshes.append(name)
        elif isinstance(asset, unreal.AnimSequence):
            animations.append(name)
        else:
            unsupported.append(f"{name} ({type(asset).__name__})")

    lines = []
    if static_meshes:
        lines.append(f"Static Meshes ({len(static_meshes)}):")
        for name in static_meshes[:5]:  # Show max 5
            lines.append(f"  - {name}")
        if len(static_meshes) > 5:
            lines.append(f"  ... and {len(static_meshes) - 5} more")

    if skeletal_meshes:
        lines.append(f"Skeletal Meshes ({len(skeletal_meshes)}):")
        for name in skeletal_meshes[:5]:
            lines.append(f"  - {name}")
        if len(skeletal_meshes) > 5:
            lines.append(f"  ... and {len(skeletal_meshes) - 5} more")

    if animations:
        lines.append(f"Animations ({len(animations)}):")
        for name in animations[:5]:
            lines.append(f"  - {name}")
        if len(animations) > 5:
            lines.append(f"  ... and {len(animations) - 5} more")

    if unsupported:
        lines.append(f"Unsupported (will be skipped) ({len(unsupported)}):")
        for name in unsupported[:3]:
            lines.append(f"  - {name}")

    return "\n".join(lines)


def _get_output_directory():
    """
    Get the output directory for export.
    Uses {ProjectDir}/GodotExport/ as the default.
    """
    project_dir = unreal.Paths.project_dir()
    # Convert to absolute path for clarity
    abs_project_dir = unreal.Paths.convert_relative_path_to_full(project_dir)
    return os.path.join(abs_project_dir, "GodotExport")


def _show_result_dialog(report, output_dir):
    """Show export results in a dialog."""
    if report.failed == 0:
        msg = (
            f"Export completed successfully!\n\n"
            f"Exported: {report.succeeded}/{report.total} assets\n"
            f"Output: {output_dir}\n\n"
            "You can now import the .glb files directly into Godot 4.x\n"
            "by dragging them into the Godot FileSystem panel."
        )
        unreal.EditorDialog.show_message(
            "Export Complete",
            msg,
            unreal.AppMsgType.OK,
        )
    else:
        msg = (
            f"Export completed with errors.\n\n"
            f"Succeeded: {report.succeeded}/{report.total}\n"
            f"Failed: {report.failed}\n\n"
        )
        for r in report.results:
            if not r.success:
                msgs = "; ".join(r.messages) if r.messages else "Unknown error"
                msg += f"- {r.asset_name}: {msgs}\n"

        msg += f"\nOutput: {output_dir}"

        unreal.EditorDialog.show_message(
            "Export Complete (with errors)",
            msg,
            unreal.AppMsgType.OK,
        )


def quick_export():
    """
    Quick export without dialog - exports selected assets to the default directory.
    Useful for scripting or toolbar quick-action buttons.
    """
    selected = unreal.EditorUtilityLibrary.get_selected_assets()
    if not selected:
        unreal.log_warning("UnrealToGodot: No assets selected.")
        return None

    output_dir = os.path.join(unreal.Paths.project_dir(), "GodotExport")

    config = ExportConfig()
    config.overwrite_existing = True

    exporter = GodotExporter(config)
    report = exporter.export_assets(list(selected), output_dir)

    unreal.log(report.summary_text())
    return report
