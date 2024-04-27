import numpy as np
import matplotlib.pyplot as plt
from tqdm.notebook import tqdm
from matplotlib.patches import Patch
from scipy.spatial import cKDTree, ConvexHull


############################################
######## DISPLAY EXISTING DATASETS #########
############################################

def read_obj_vertices(filename):
    """
    Reads a .obj file and extracts the vertices into a NumPy array.

    Parameters:
    - filename: str, the path to the .obj file.

    Returns:
    - A NumPy array of shape (nverts, 3) containing the vertex positions.
    """
    vertices = []  # Initialize an empty list to store vertices
    with open(filename, 'r') as file:
        for line in file:
            parts = line.split()  # Split the line into parts
            if len(parts) < 4 or parts[0] != 'v':
                continue  # Ignore lines that are not vertex definitions
            # Convert the x, y, z coordinates to float and add to the vertices list
            vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])

    return np.array(vertices)


def plot_vertex_overlaps_with_hulls(arrays, labels, colors):
    """
    Plots the overlap of five (nverts, 3) arrays in 2D by dropping the z-coordinate.
    Additionally, plots the convex hulls of each array in a second figure.

    Parameters:
    - arrays: list of np.ndarray, each with shape (nverts, 3).
    - labels: list of str, labels for each array.
    """
      # Different color for each array
    alpha = 0.05  # Transparency level for each plot

    fig, axs = plt.subplots(1, 2, figsize=(20, 8))  # Create two subplots side by side

    # First subplot for the scatter plot
    for array, color, label in zip(arrays, colors, labels):
        axs[0].scatter(array[:, 0], array[:, 1], color=color, alpha=alpha, s=0.05, label=label)

    legend_patches = [Patch(color=color, label=label) for color, label in zip(colors, labels)]
    axs[0].legend(handles=legend_patches, loc='upper right')

    axs[0].set_xlabel('X (Easting)')
    axs[0].set_ylabel('Y (Northing)')
    axs[0].set_title('Overlap of Vertex Arrays in 2D')

    # Second subplot for the convex hulls
    for array, color in zip(arrays, colors):
        if len(array) > 2:  # A convex hull requires at least 3 points
            hull = ConvexHull(array[:, :2])
            for simplex in hull.simplices:
                axs[1].plot(array[simplex, 0], array[simplex, 1], color=color, linewidth=2)
            #print("Area of convex hull:", hull.area) # Doesnt seem to work, the area is overestimated

    axs[1].set_xlabel('X (Easting)')
    axs[1].set_ylabel('Y (Northing)')
    axs[1].set_title('Convex Hulls of Arrays')

    plt.show()


def plot_patches_comparison(patches, ref_index, dist, colors, labels):
    """
    Compares a reference patch against all other patches based on XY distance,
    visualizes altitude differences using the RdBu colormap,
    and displays convex hull borders with the color associated to each patch.
    The color scale is fixed between -30m and 30m.

    Parameters:
    - patches: list of np.ndarray, each with shape (nverts, 3), representing XYZ coordinates.
    - ref_index: int, index of the reference patch in the list.
    - dist: float, distance threshold to define overlaps in the XY plane.
    - colors: list of str, colors for each patch.
    - labels: list of str, labels for each patch.
    """
    ref_patch = patches[ref_index]
    tree1 = cKDTree(ref_patch[:, :2])
    num_comparisons = len(patches) - 1  # Excluding comparison with itself

    fig, axs = plt.subplots(1, num_comparisons, figsize=(5*num_comparisons, 4), squeeze=False)

    for i, patch in enumerate(patches):
        if i == ref_index:
            continue  # Skip the reference patch

        indices = tree1.query_ball_point(patch[:, :2], dist)
        altitude_diffs = []  # Differences in altitude
        positions = []  # Positions for plotting

        for point_idx, point_indices in enumerate(indices):
            if point_indices:  # If there are overlapping points
                ref_point_idx = point_indices[0]  # Assuming closest point for comparison
                altitude_diff = patch[point_idx, 2] - ref_patch[ref_point_idx, 2]
                altitude_diffs.append(altitude_diff)
                positions.append(patch[point_idx, :2])

        # Calculate average altitude difference for the title
        avg_alt_diff = np.mean(altitude_diffs) if altitude_diffs else 0

        subplot_idx = i-1 if i > ref_index else i  # Adjust subplot index after skipping ref patch

        if positions:  # If there are overlapping points to plot
            positions = np.array(positions)
            altitude_diffs = np.clip(altitude_diffs, -30, 30)  # Clip values to be within [-30, 30]
            sc = axs[0, subplot_idx].scatter(positions[:, 0], positions[:, 1], c=altitude_diffs, cmap='RdBu', vmin=-30, vmax=30, s=50)
            cbar = fig.colorbar(sc, ax=axs[0, subplot_idx], label='Altitude Difference')
            cbar.set_ticks([-30, 0, 30])
            cbar.set_ticklabels(['< -30', '0', '> 30'])

        # Plot the convex hulls for the reference patch and the current patch with their colors
        for p, c in [(ref_patch, colors[ref_index]), (patch, colors[i])]:
            hull = ConvexHull(p[:, :2])
            for simplex in hull.simplices:
                axs[0, subplot_idx].plot(p[simplex, 0], p[simplex, 1], color=c, linewidth=1.5)

        axs[0, subplot_idx].set_title(f'{labels[ref_index]} vs. {labels[i]}\nAvg Diff: {avg_alt_diff:.2f}')
        axs[0, subplot_idx].set_xticks(np.linspace(axs[0, subplot_idx].get_xlim()[0], axs[0, subplot_idx].get_xlim()[1], 3))
        axs[0, subplot_idx].set_xlabel('X')
        axs[0, subplot_idx].set_ylabel('Y')

    plt.tight_layout()
    plt.show()
