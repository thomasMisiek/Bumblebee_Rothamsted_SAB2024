import os
import numpy as np
from tqdm.notebook import tqdm
from scipy.spatial import Delaunay, KDTree

############################################
######## DISPLAY EXISTING DATASETS #########
############################################

def remove_overlaps_and_adjust_altitudes(in_coords, out_coords, proximity_threshold, average_distance_threshold):
    """
    Remove overlapping points from 'out_coords' and adjust altitudes based on proximity to 'in_coords'.

    This function first identifies points in 'out_coords' that are within a specified 'proximity_threshold'
    to any point in 'in_coords', suppressing these overlapping points to prevent redundancy.
    For points not suppressed and within 'average_distance_threshold', their altitudes are adjusted by averaging
    with the altitudes of nearby points, enhancing spatial consistency among points that are close together.

    Points beyond 'average_distance_threshold' retain their original altitudes, ensuring only relevant
    adjustments are made.

    Parameters:
    - in_coords (np.ndarray): Reference coordinates for comparison, maintaining their original state.
    - out_coords (np.ndarray): Coordinates to be processed for overlap removal and altitude adjustment.
    - proximity_threshold (float): Minimum distance between points to consider them overlapping.
    - average_distance_threshold (float): Distance within which to average altitudes for non-overlapping points.

    Returns:
    - Tuple[np.ndarray, np.ndarray]: Unchanged 'in_coords' and processed 'out_coords' with overlaps removed
      and relevant altitudes adjusted.
    """
    in_coords_np = np.array(in_coords)
    out_coords_np = np.array(out_coords)

    # Efficient nearest neighbor searches using KDTree for 'in_coords'
    in_coords_tree = KDTree(in_coords_np[:, :2])

    # Preparing combined coordinates for processing altitude adjustments
    combined_coords = np.concatenate([in_coords, out_coords])
    combined_coords_tree = KDTree(combined_coords[:, :2])

    adjusted_out_coords = []

    for point in tqdm(out_coords_np, desc="Removing Overlaps and Adjusting Altitudes"):
        # Identify nearest point in 'in_coords' considering only x and y dimensions
        distance, _ = in_coords_tree.query(point[:2])

        if distance >= proximity_threshold:
            if distance < average_distance_threshold:
                # Altitude adjustment through averaging within 'average_distance_threshold'
                indices = combined_coords_tree.query_ball_point(point[:2], r=average_distance_threshold)
                avg_altitude = np.mean(combined_coords[indices, 2])
                adjusted_point = np.array([point[0], point[1], avg_altitude])
            else:
                # Retaining original altitude for points beyond the averaging threshold
                adjusted_point = point

            adjusted_out_coords.append(adjusted_point)

    return in_coords_np, np.array(adjusted_out_coords)


def create_obj_from_vertices(vertices, new_file_name, mtl_file_name, materials_names, color=(1, 1, 1)):
    assert vertices.shape[1] == 6, "Vertices array must include 6 dimensions."

    spatial_vertices = vertices[:, :3]  # Use x, y, and z for Delaunay triangulation
    tri = Delaunay(spatial_vertices[:, :2])  # Triangulation based on x and y

    material_indices = vertices[:, 5].astype(int)

    with open(new_file_name, 'w') as file:
        file.write(f"mtllib {mtl_file_name}\n\n")

        # Write all vertices and texture vertices
        for vertex in tqdm(vertices, desc="Writing vertices and texture coordinates"):
            file.write(f"v {vertex[0]} {vertex[1]} {vertex[2]} {color[0]} {color[1]} {color[2]}\n")
            file.write(f"vt {vertex[3]} {vertex[4]}\n")

        current_material_index = -1

        # Sort faces to minimize material changes
        def sort_key(face):
            face_materials = material_indices[face]
            return (len(set(face_materials)), np.min(face_materials))

        mixed_faces = []
        for face in tqdm(sorted(tri.simplices, key=sort_key), desc="Processing faces"):
            face_material_indices = material_indices[face]
            if len(set(face_material_indices)) == 1:
                # Single material face, handle as before
                material_index = face_material_indices[0]
                if current_material_index != material_index:
                    current_material_index = material_index
                    material_name = materials_names[current_material_index-1]
                    file.write(f"\nusemtl {material_name}\n")
                face_vertices = ' '.join(f"{v_idx+1}/{v_idx+1}" for v_idx in face)
                file.write(f"f {face_vertices}\n")
            else:
                # Mixed materials face, store for later processing
                mixed_faces.append(face)

        # Process mixed material faces
        if mixed_faces:
            # Assuming the first material from the mixed faces is used for consistency
            chosen_material_index = material_indices[mixed_faces[0][0]]
            chosen_material_name = materials_names[chosen_material_index-1]
            if current_material_index != chosen_material_index:
                file.write(f"\nusemtl {chosen_material_name}\n")

            for face in mixed_faces:
                face_vertices = ' '.join(f"{v_idx+1}/{v_idx+1}" for v_idx in face)
                file.write(f"f {face_vertices}\n")
