"""
Asset dependency resolver.

Analyzes Unreal assets and collects all related dependencies:
- StaticMesh  -> Materials -> Textures
- SkeletalMesh -> Skeleton, Materials -> Textures
- AnimSequence -> Skeleton -> SkeletalMesh (optional preview mesh)
"""

import unreal


class AssetDependencyInfo:
    """Holds an asset and its resolved dependencies."""

    def __init__(self, asset, asset_path):
        self.asset = asset
        self.asset_path = asset_path
        self.asset_name = asset.get_name()
        self.asset_type = type(asset).__name__
        self.materials = []
        self.textures = []
        self.skeleton = None
        self.skeletal_mesh = None  # Preview mesh for animations
        self.animations = []


class DependencyResolver:
    """Resolves dependencies for Unreal assets before export."""

    def resolve(self, asset):
        """
        Resolve all dependencies for a given asset.

        Args:
            asset: An Unreal asset object (StaticMesh, SkeletalMesh, or AnimSequence)

        Returns:
            AssetDependencyInfo with all resolved dependencies
        """
        asset_path = asset.get_path_name()
        info = AssetDependencyInfo(asset, asset_path)

        if isinstance(asset, unreal.StaticMesh):
            self._resolve_static_mesh(asset, info)
        elif isinstance(asset, unreal.SkeletalMesh):
            self._resolve_skeletal_mesh(asset, info)
        elif isinstance(asset, unreal.AnimSequence):
            self._resolve_animation(asset, info)
        else:
            unreal.log_warning(
                f"UnrealToGodot: Unsupported asset type '{info.asset_type}' "
                f"for '{info.asset_name}'"
            )

        return info

    def _resolve_static_mesh(self, mesh, info):
        """Resolve materials and textures from a StaticMesh."""
        info.materials = self._get_materials_from_static_mesh(mesh)
        info.textures = self._get_textures_from_materials(info.materials)

        unreal.log(
            f"UnrealToGodot: StaticMesh '{info.asset_name}' -> "
            f"{len(info.materials)} materials, {len(info.textures)} textures"
        )

    def _resolve_skeletal_mesh(self, mesh, info):
        """Resolve skeleton, materials and textures from a SkeletalMesh."""
        info.skeleton = mesh.skeleton
        info.materials = self._get_materials_from_skeletal_mesh(mesh)
        info.textures = self._get_textures_from_materials(info.materials)

        skeleton_name = info.skeleton.get_name() if info.skeleton else "None"
        unreal.log(
            f"UnrealToGodot: SkeletalMesh '{info.asset_name}' -> "
            f"Skeleton: {skeleton_name}, "
            f"{len(info.materials)} materials, {len(info.textures)} textures"
        )

    def _resolve_animation(self, anim, info):
        """Resolve skeleton and optionally preview mesh from an AnimSequence."""
        info.skeleton = anim.get_editor_property("skeleton")

        if info.skeleton:
            # Try to find a SkeletalMesh that uses this skeleton as preview mesh
            preview_mesh = self._find_preview_mesh_for_skeleton(info.skeleton)
            if preview_mesh:
                info.skeletal_mesh = preview_mesh
                info.materials = self._get_materials_from_skeletal_mesh(preview_mesh)
                info.textures = self._get_textures_from_materials(info.materials)

        skeleton_name = info.skeleton.get_name() if info.skeleton else "None"
        preview_name = info.skeletal_mesh.get_name() if info.skeletal_mesh else "None"
        unreal.log(
            f"UnrealToGodot: AnimSequence '{info.asset_name}' -> "
            f"Skeleton: {skeleton_name}, Preview Mesh: {preview_name}"
        )

    def _get_materials_from_static_mesh(self, mesh):
        """Extract all MaterialInterface references from a StaticMesh."""
        materials = []
        static_materials = mesh.static_materials
        for static_mat in static_materials:
            mat = static_mat.material_interface
            if mat and mat not in materials:
                materials.append(mat)
        return materials

    def _get_materials_from_skeletal_mesh(self, mesh):
        """Extract all MaterialInterface references from a SkeletalMesh."""
        materials = []
        skel_materials = mesh.materials
        for skel_mat in skel_materials:
            mat = skel_mat.material_interface
            if mat and mat not in materials:
                materials.append(mat)
        return materials

    def _get_textures_from_materials(self, materials):
        """Extract all Texture references from a list of materials."""
        textures = []
        for mat in materials:
            try:
                used_textures = unreal.MaterialEditingLibrary.get_used_textures(mat)
                for tex in used_textures:
                    if tex and tex not in textures:
                        textures.append(tex)
            except Exception as e:
                unreal.log_warning(
                    f"UnrealToGodot: Could not get textures from material "
                    f"'{mat.get_name()}': {e}"
                )
        return textures

    def _find_preview_mesh_for_skeleton(self, skeleton):
        """
        Find a SkeletalMesh that uses the given skeleton.
        Checks the skeleton's preview mesh first, then searches the asset registry.
        """
        # Try to get the preview mesh directly from the skeleton
        try:
            preview_mesh = skeleton.get_editor_property("preview_skeletal_mesh")
            if preview_mesh:
                return preview_mesh
        except Exception:
            pass

        # Fallback: search the asset registry for a SkeletalMesh with this skeleton
        registry = unreal.AssetRegistryHelpers.get_asset_registry()
        skeleton_path = skeleton.get_path_name()

        ar_filter = unreal.ARFilter(
            class_names=["SkeletalMesh"],
            recursive_classes=True
        )
        asset_data_list = registry.get_assets(ar_filter)

        for asset_data in asset_data_list:
            try:
                skel_mesh = asset_data.get_asset()
                if skel_mesh and skel_mesh.skeleton == skeleton:
                    return skel_mesh
            except Exception:
                continue

        return None

    def resolve_batch(self, assets):
        """
        Resolve dependencies for multiple assets.

        Args:
            assets: List of Unreal asset objects

        Returns:
            List of AssetDependencyInfo
        """
        results = []
        for asset in assets:
            info = self.resolve(asset)
            results.append(info)
        return results
