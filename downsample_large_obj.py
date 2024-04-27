import numpy as np
from tqdm.notebook import tqdm

##################################
#### DOWNSAMPLING LARGE .OBJ #####
##################################

def read_obj_and_find_highest_points(obj_file_path, nbinsX, nbinsY, x_bounds, y_bounds):
    """
    Reads a .obj file and finds the highest point in each bin of a 2D grid within specified bounds.

    Args:
        obj_file_path (str): Path to the .obj file.
        nbinsX (int): Number of bins along the x-axis.
        nbinsY (int): Number of bins along the y-axis.
        x_bounds (tuple): Bounds along the x-axis as (min, max).
        y_bounds (tuple): Bounds along the y-axis as (min, max).

    Returns:
        np.ndarray: 2D array containing [x, y, z, id] for the highest point in each bin.
    """
    # Initialize the grid to store the highest points
    highest_points = np.empty((nbinsX, nbinsY, 4), dtype=object)

    # Create linspace for x and y dimensions
    x_linspace = np.linspace(x_bounds[0], x_bounds[1], nbinsX + 1)
    y_linspace = np.linspace(y_bounds[0], y_bounds[1], nbinsY + 1)

    with open(obj_file_path, 'r') as file:
        vertex_id = 0
        for line in tqdm(file):
            # Process only vertex definitions
            if line.startswith('v '):
                vertex_id += 1
                parts = line.split()
                x, y, z = map(float, parts[1:4])

                # Find the bin indices for the vertex
                x_index = np.searchsorted(x_linspace, x, side='right') - 1
                y_index = np.searchsorted(y_linspace, y, side='right') - 1

                # Skip vertices outside the specified bounds
                if x_index == nbinsX or y_index == nbinsY or x_index < 0 or y_index < 0:
                    continue

                current_point = highest_points[x_index, y_index]
                # Update the bin with the new highest point if necessary
                if current_point[0] is None or z > current_point[2]:
                    highest_points[x_index, y_index] = [x, y, z, vertex_id]

    # Filter out empty bins
    filtered_points = np.array([point for sublist in highest_points for point in sublist if point[0] is not None])

    return filtered_points


def associate_vt_ids(obj_file_path, highest_points):
    """
    Reads a .obj file to associate a texture vertex ID (vt) with each vertex ID (v)
    based on face definitions, updating the highest points with vt IDs, and including the number of the
    current usemtl line associated with the face. Also returns a list of usemtl names.

    Args:
        obj_file_path (str): Path to the .obj file.
        highest_points (np.ndarray): Array containing [x, y, z, v_id] for highest points.

    Returns:
        tuple: A tuple containing:
               - np.ndarray: Updated array including [x, y, z, v_id, vt_id, usemtl_num] for each highest point.
               - list: List of usemtl names in the order they were encountered.
    """
    v_to_highest_point = {int(point[3]): point.tolist() for point in highest_points}
    v_to_vt = {}
    usemtl_count = 0
    usemtl_names = []
    current_usemtl = None

    with open(obj_file_path, 'r') as file:
        for line in tqdm(file):
            if line.startswith('usemtl '):
                usemtl_count += 1
                current_usemtl = line.strip().split(' ', 1)[1]
                if current_usemtl not in usemtl_names:
                    usemtl_names.append(current_usemtl)
            elif line.startswith('f '):
                parts = line.split()[1:]
                for part in parts:
                    v_id, vt_id, *_ = (part.split('/') + [None, None])[:3]
                    v_id = int(v_id)
                    if v_id in v_to_highest_point and vt_id is not None:
                        if v_id not in v_to_vt:
                            v_to_vt[v_id] = int(vt_id)
                            # Include usemtl count for this vertex
                            v_to_highest_point[v_id].extend([int(vt_id), usemtl_count])

    # Ensure each point has a 6th dimension; fill with 0 if missing (no material)
    for v_id, data in v_to_highest_point.items():
        if len(data) == 5:  # If vt_id was added but not usemtl_num
            data.append(0)  # Default to 0 (no material)

    updated_highest_points = np.array(list(v_to_highest_point.values()), dtype=object)

    return updated_highest_points, usemtl_names


def associate_vertex_to_texture_coords(obj_file_path, highest_points_with_vt):
    """
    Reads a .obj file to map each vertex's coordinates (xv, yv, zv) to its texture
    vertex coordinates (xvt, yvt), using the output from the previous function that
    includes [x, y, z, v_id, vt_id, usemtl_num].

    Args:
        obj_file_path (str): Path to the .obj file.
        highest_points_with_vt (np.ndarray): Array containing [x, y, z, v_id, vt_id, usemtl_num] for highest points.

    Returns:
        np.ndarray: Array containing [xv, yv, zv, xvt, yvt, usemtl_num] for each vertex.
    """
    # Extract v_id to vt_id and usemtl_num mapping
    v_id_to_vt_id_and_usemtl_num = {int(point[3]): (int(point[4]), int(point[5])) for point in highest_points_with_vt if len(point) > 5}

    # Initialize lists to hold vertex and texture vertex coordinates
    v_coords = []
    vt_coords = []

    with open(obj_file_path, 'r') as file:
        for line in tqdm(file):
            parts = line.split()
            if line.startswith('v ') and len(parts) >= 4:
                # Add vertex coordinates to list
                v_coords.append(np.array(parts[1:4], dtype=float))
            elif line.startswith('vt ') and len(parts) >= 3:
                # Add texture vertex coordinates to list
                vt_coords.append(np.array(parts[1:3], dtype=float))

    # Prepare the final output
    final_mapping = []
    for v_id, (vt_id, usemtl_num) in tqdm(v_id_to_vt_id_and_usemtl_num.items()):
        # Check if the IDs are valid (within bounds of their respective lists)
        if v_id <= len(v_coords) and vt_id <= len(vt_coords):
            xv, yv, zv = v_coords[v_id - 1]  # Adjust for zero-based indexing
            xvt, yvt = vt_coords[vt_id - 1]  # Adjust for zero-based indexing
            final_mapping.append([xv, yv, zv, xvt, yvt, usemtl_num])

    return np.array(final_mapping, dtype=float)
