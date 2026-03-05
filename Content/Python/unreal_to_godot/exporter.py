"""
Core export logic for Unreal-to-Godot asset migration.

Uses unreal.GLTFExporter to export assets to glTF 2.0 format,
with automatic dependency resolution and organized output structure.
"""

import os
import json
import unreal

from unreal_to_godot.config import ExportConfig
from unreal_to_godot.dependency_resolver import DependencyResolver


class ExportResult:
    """Result of a single asset export."""

    def __init__(self, asset_name, asset_type, success, output_path="", messages=None):
        self.asset_name = asset_name
        self.asset_type = asset_type
        self.success = success
        self.output_path = output_path
        self.messages = messages or []

    def to_dict(self):
        return {
            "asset_name": self.asset_name,
            "asset_type": self.asset_type,
            "success": self.success,
            "output_path": self.output_path,
            "messages": self.messages,
        }


class ExportReport:
    """Summary report of a batch export operation."""

    def __init__(self):
        self.results = []
        self.total = 0
        self.succeeded = 0
        self.failed = 0

    def add_result(self, result):
        self.results.append(result)
        self.total += 1
        if result.success:
            self.succeeded += 1
        else:
            self.failed += 1

    def to_dict(self):
        return {
            "total": self.total,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "assets": [r.to_dict() for r in self.results],
        }

    def summary_text(self):
        lines = [
            f"Export Complete: {self.succeeded}/{self.total} succeeded",
        ]
        if self.failed > 0:
            lines.append(f"  Failed: {self.failed}")
            for r in self.results:
                if not r.success:
                    msgs = "; ".join(r.messages) if r.messages else "Unknown error"
                    lines.append(f"    - {r.asset_name} ({r.asset_type}): {msgs}")
        return "\n".join(lines)


class GodotExporter:
    """Exports Unreal assets to glTF for Godot Engine."""

    # Subfolder names per asset type
    TYPE_FOLDERS = {
        "StaticMesh": "StaticMeshes",
        "SkeletalMesh": "SkeletalMeshes",
        "AnimSequence": "Animations",
        "Texture2D": "Textures",
    }

    def __init__(self, config=None):
        self.config = config or ExportConfig()
        self.resolver = DependencyResolver()

    def export_selected_assets(self, output_directory):
        """
        Export all currently selected assets in the Content Browser.

        Args:
            output_directory: Root output folder path

        Returns:
            ExportReport with results for each asset
        """
        self.config.output_directory = output_directory
        selected = unreal.EditorUtilityLibrary.get_selected_assets()

        if not selected:
            unreal.log_warning("UnrealToGodot: No assets selected in Content Browser.")
            report = ExportReport()
            return report

        return self.export_assets(list(selected), output_directory)

    def export_assets(self, assets, output_directory):
        """
        Export a list of assets to glTF.

        Args:
            assets: List of Unreal asset objects
            output_directory: Root output folder path

        Returns:
            ExportReport with results for each asset
        """
        self.config.output_directory = output_directory
        report = ExportReport()

        # Filter to supported asset types
        supported_assets = []
        for asset in assets:
            if isinstance(asset, (unreal.StaticMesh, unreal.SkeletalMesh, unreal.AnimSequence, unreal.Texture2D)):
                supported_assets.append(asset)
            else:
                type_name = type(asset).__name__
                report.add_result(ExportResult(
                    asset.get_name(), type_name, False,
                    messages=[f"Unsupported asset type: {type_name}"]
                ))

        if not supported_assets:
            unreal.log_warning("UnrealToGodot: No supported assets to export.")
            return report

        total = len(supported_assets)
        unreal.log(f"UnrealToGodot: Starting export of {total} asset(s)...")

        # Create progress dialog
        with unreal.ScopedSlowTask(total, "Exporting to Godot...") as slow_task:
            slow_task.make_dialog(True)

            for asset in supported_assets:
                if slow_task.should_cancel():
                    unreal.log_warning("UnrealToGodot: Export cancelled by user.")
                    break

                slow_task.enter_progress_frame(
                    1, f"Exporting {asset.get_name()}..."
                )

                result = self._export_single_asset(asset)
                report.add_result(result)

        # Generate manifest
        if self.config.generate_manifest:
            self._write_manifest(output_directory, report)

        # Log summary
        unreal.log(report.summary_text())

        return report

    def _export_single_asset(self, asset):
        """
        Export a single asset to glTF.

        Args:
            asset: An Unreal asset object

        Returns:
            ExportResult
        """
        asset_name = asset.get_name()
        asset_type = type(asset).__name__

        # Handle Texture2D directly as PNG export
        if isinstance(asset, unreal.Texture2D):
            return self._export_single_texture(asset)

        # Resolve dependencies
        dep_info = self.resolver.resolve(asset)

        # Determine output path
        output_path = self._get_output_path(asset_name, asset_type)

        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)

        # Check overwrite
        if os.path.exists(output_path) and not self.config.overwrite_existing:
            return ExportResult(
                asset_name, asset_type, False, output_path,
                messages=["File already exists (overwrite disabled)"]
            )

        # Select appropriate export options
        if isinstance(asset, unreal.AnimSequence) and not self.config.include_preview_mesh_with_anim:
            gltf_options = self.config.create_anim_only_options()
        else:
            gltf_options = self.config.create_gltf_options()

        # Execute glTF export
        try:
            export_messages = unreal.GLTFExporter.export_to_gltf(
                asset,
                output_path,
                gltf_options,
                set()  # selected_actors (not used for asset export)
            )

            # Parse export messages
            messages = self._parse_export_messages(export_messages)
            success = os.path.exists(output_path)

            if success:
                unreal.log(f"UnrealToGodot: Exported '{asset_name}' -> {output_path}")

                # Export textures as separate PNG files
                if self.config.export_textures_as_png and dep_info.textures:
                    tex_dir = os.path.join(output_dir, "Textures")
                    exported_count = self._export_textures_as_png(
                        dep_info.textures, tex_dir
                    )
                    if exported_count > 0:
                        messages.append(f"Exported {exported_count} texture(s) as PNG")
            else:
                messages.append("Export completed but output file not found")

            return ExportResult(asset_name, asset_type, success, output_path, messages)

        except Exception as e:
            error_msg = str(e)
            unreal.log_error(
                f"UnrealToGodot: Failed to export '{asset_name}': {error_msg}"
            )
            return ExportResult(
                asset_name, asset_type, False, output_path,
                messages=[error_msg]
            )

    def _get_output_path(self, asset_name, asset_type):
        """
        Build the output file path for an asset.

        If organize_by_type is True:
            output_dir/StaticMeshes/SM_Chair/SM_Chair.glb
        Otherwise:
            output_dir/SM_Chair/SM_Chair.glb
        """
        ext = self.config.get_file_extension()
        parts = [self.config.output_directory]

        if self.config.organize_by_type:
            type_folder = self.TYPE_FOLDERS.get(asset_type, "Other")
            parts.append(type_folder)

        parts.append(asset_name)
        parts.append(f"{asset_name}{ext}")

        return os.path.join(*parts)

    def _export_single_texture(self, texture):
        """
        Export a single Texture2D asset as PNG.

        Args:
            texture: A Texture2D asset

        Returns:
            ExportResult
        """
        tex_name = texture.get_name()
        asset_type = "Texture2D"

        # Build output path: Textures/T_Name/T_Name.png
        parts = [self.config.output_directory]
        if self.config.organize_by_type:
            parts.append("Textures")
        parts.append(tex_name)
        parts.append(f"{tex_name}.png")
        output_path = os.path.join(*parts)

        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)

        if os.path.exists(output_path) and not self.config.overwrite_existing:
            return ExportResult(
                tex_name, asset_type, False, output_path,
                messages=["File already exists (overwrite disabled)"]
            )

        try:
            task = unreal.AssetExportTask()
            task.object = texture
            task.filename = output_path
            task.automated = True
            task.replace_identical = True
            task.prompt = False

            success = unreal.Exporter.run_asset_export_task(task)
            if success:
                unreal.log(f"UnrealToGodot: Texture '{tex_name}' -> {output_path}")
                return ExportResult(tex_name, asset_type, True, output_path)
            else:
                return ExportResult(
                    tex_name, asset_type, False, output_path,
                    messages=["AssetExportTask returned false"]
                )
        except Exception as e:
            return ExportResult(
                tex_name, asset_type, False, output_path,
                messages=[str(e)]
            )

    def _export_textures_as_png(self, textures, output_dir):
        """
        Export texture assets as separate PNG files.

        Args:
            textures: List of Texture assets
            output_dir: Directory to save PNG files

        Returns:
            Number of successfully exported textures
        """
        os.makedirs(output_dir, exist_ok=True)
        exported = 0

        for texture in textures:
            tex_name = texture.get_name()
            png_path = os.path.join(output_dir, f"{tex_name}.png")

            if os.path.exists(png_path) and not self.config.overwrite_existing:
                exported += 1
                continue

            try:
                task = unreal.AssetExportTask()
                task.object = texture
                task.filename = png_path
                task.automated = True
                task.replace_identical = True
                task.prompt = False

                success = unreal.Exporter.run_asset_export_task(task)
                if success:
                    exported += 1
                    unreal.log(f"UnrealToGodot: Texture '{tex_name}' -> {png_path}")
                else:
                    unreal.log_warning(
                        f"UnrealToGodot: Failed to export texture '{tex_name}'"
                    )
            except Exception as e:
                unreal.log_warning(
                    f"UnrealToGodot: Error exporting texture '{tex_name}': {e}"
                )

        return exported

    def _parse_export_messages(self, export_messages):
        """Extract message strings from GLTFExportMessages."""
        messages = []
        if export_messages is None:
            return messages

        try:
            # GLTFExportMessages has suggestions/warnings/errors
            suggestions = export_messages.get_editor_property("suggestions")
            warnings = export_messages.get_editor_property("warnings")
            errors = export_messages.get_editor_property("errors")

            if suggestions:
                for msg in suggestions:
                    messages.append(f"[Info] {msg}")
            if warnings:
                for msg in warnings:
                    messages.append(f"[Warning] {msg}")
            if errors:
                for msg in errors:
                    messages.append(f"[Error] {msg}")
        except Exception:
            # If the API doesn't match expected structure, just note it
            pass

        return messages

    def _write_manifest(self, output_directory, report):
        """Write a manifest.json file with export metadata."""
        manifest_path = os.path.join(output_directory, "manifest.json")
        manifest = {
            "exporter": "UnrealToGodotExporter",
            "version": "1.0.0",
            "format": self.config.output_format,
            "export": report.to_dict(),
        }

        try:
            os.makedirs(output_directory, exist_ok=True)
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
            unreal.log(f"UnrealToGodot: Manifest written to {manifest_path}")
        except Exception as e:
            unreal.log_warning(f"UnrealToGodot: Failed to write manifest: {e}")
