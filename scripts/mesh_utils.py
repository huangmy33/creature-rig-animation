"""Scene geometry utilities: include node transforms and mesh instances."""
import numpy as np
import trimesh


def scene_mesh(scene):
    meshes = []
    for node in scene.graph.nodes_geometry:
        transform, geometry_name = scene.graph[node]
        geometry = scene.geometry[geometry_name]
        if isinstance(geometry, trimesh.Trimesh):
            copy = geometry.copy()
            copy.apply_transform(transform)
            meshes.append(copy)
    if not meshes:
        raise ValueError("GLB contains no triangle mesh")
    mesh = trimesh.util.concatenate(meshes)
    if not len(mesh.vertices) or not len(mesh.faces) or not np.isfinite(mesh.vertices).all():
        raise ValueError("GLB has empty or non-finite mesh geometry")
    return mesh
