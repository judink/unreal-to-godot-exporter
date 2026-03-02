"""
Export configuration optimized for Godot Engine compatibility.

Provides default GLTFExportOptions and user-configurable settings
for the Unreal-to-Godot asset export pipeline.
"""

import unreal


# Output format options
FORMAT_GLTF = "gltf"  # JSON text + separate binary/texture files
FORMAT_GLB = "glb"    # Single self-contained binary file


class ExportConfig:
    """Manages export settings for the Unreal-to-Godot pipeline."""

    def __init__(self):
        self.output_directory = ""
        self.output_format = FORMAT_GLB
        self.organize_by_type = True  # Create subfolders per asset type
        self.generate_manifest = True  # Create manifest.json with export info
        self.include_dependencies = True  # Auto-include materials/textures
        self.include_preview_mesh_with_anim = True  # Export preview mesh with animations
        self.overwrite_existing = False

    def create_gltf_options(self):
        """Create GLTFExportOptions optimized for Godot compatibility."""
        options = unreal.GLTFExportOptions()

        # Scale: UE uses centimeters, Godot/glTF use meters
        options.export_uniform_scale = 0.01

        # Normal maps: flip green channel from UE convention to glTF convention
        options.adjust_normalmaps = True

        # Skeletal mesh support
        options.export_vertex_skin_weights = True
        options.make_skinned_meshes_root = True

        # Material handling: bake UE node-graph materials to PBR textures
        options.bake_material_inputs = unreal.GLTFMaterialBakeMode.ENABLED

        # Texture settings
        options.texture_image_format = unreal.GLTFTextureImageFormat.PNG

        # Include preview mesh when exporting standalone animations
        options.export_preview_mesh = self.include_preview_mesh_with_anim

        # Additional material support
        options.export_unlit_materials = True
        options.export_clear_coat_materials = True
        options.export_texture_transforms = True
        options.export_emissive_strength = True

        # Mesh settings
        options.export_vertex_colors = False  # Can cause artifacts in Godot
        options.default_level_of_detail = 0  # Highest quality LOD

        # Don't export things we don't need
        options.export_cameras = False
        options.export_lights = False
        options.export_hidden_in_game = False

        return options

    def create_anim_only_options(self):
        """Create options for exporting animation without mesh data."""
        options = self.create_gltf_options()
        options.export_preview_mesh = False
        return options

    def get_file_extension(self):
        """Return the file extension based on selected output format."""
        return ".glb" if self.output_format == FORMAT_GLB else ".gltf"
