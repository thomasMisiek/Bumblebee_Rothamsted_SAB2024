import os
import cv2
import glob
import numpy as np
from PIL import Image
import geopandas as gpd
import matplotlib.pyplot as plt
from tqdm.notebook import tqdm
from scipy.spatial import KDTree


def sample_and_filter_coordinates(n=50000, center=(2500, 2500), matrix_size=(5000, 5000), scale=1000):

    coords = np.random.normal(loc=center, scale=scale, size=(n, 2))
    coords = np.array([coord for coord in coords if 0 <= coord[0] <= matrix_size[0] and 0 <= coord[1] <= matrix_size[1]])
    tree = KDTree(coords)
    return coords, tree

def classify_and_analyze_distances(coords, center=(2500, 2500), periphery_bounds=(2000, 2500), center_bounds=(0, 500)):

    distances_from_center = np.sqrt((coords[:, 0] - center[0])**2 + (coords[:, 1] - center[1])**2)
    periphery_mask = (distances_from_center >= periphery_bounds[0]) & (distances_from_center <= periphery_bounds[1])
    center_mask = (distances_from_center >= center_bounds[0]) & (distances_from_center <= center_bounds[1])

    periphery_coords = coords[periphery_mask]
    center_coords = coords[center_mask]

    periphery_distances = center_distances = np.array([])
    if len(periphery_coords) > 1:
        periphery_tree = KDTree(periphery_coords)
        periphery_distances = periphery_tree.query(periphery_coords, k=2)[0][:, 1]
        max_periphery_distance = np.max(periphery_distances)
        avg_periphery_distance = np.mean(periphery_distances)
    else:
        max_periphery_distance = avg_periphery_distance = 0

    if len(center_coords) > 1:
        center_tree = KDTree(center_coords)
        center_distances = center_tree.query(center_coords, k=2)[0][:, 1]
        max_center_distance = np.max(center_distances)
        avg_center_distance = np.mean(center_distances)
    else:
        max_center_distance = avg_center_distance = 0

    results = {
        'max_periphery_distance': max_periphery_distance,
        'avg_periphery_distance': avg_periphery_distance,
        'max_center_distance': max_center_distance,
        'avg_center_distance': avg_center_distance,
        'total_datapoints': len(coords)
    }

    # Display histograms for the distances
    # Create a 2D histogram
    plt.figure(figsize=(8, 6))
    plt.hist2d(coords[:,0], coords[:,1], bins=30, cmap='Blues')
    cb = plt.colorbar()
    cb.set_label('counts in bin')

    plt.xlabel('X')
    plt.ylabel('Y')
    plt.title('2D Histogram of Coordinates')
    plt.show()

    # Display histograms for the distances
    plt.hist(periphery_distances, bins=30, alpha=0.5, label='Periphery Distances | d to origin'+str(periphery_bounds))
    plt.ylabel("Unit counts")
    plt.xlabel("Distance between closest points")
    plt.legend()
    plt.show()

    plt.hist(center_distances, bins=30, alpha=0.5, label='Center Distances | d to origin='+str(center_bounds))
    plt.legend()
    plt.ylabel("Unit counts")
    plt.xlabel("Distance between closest points")
    plt.show()

    print(f"Maximum distance between points at the periphery: {results['max_periphery_distance']}")
    print(f"Average distance between points at the periphery: {results['avg_periphery_distance']}")
    print(f"Maximum distance between points at the center: {results['max_center_distance']}")
    print(f"Average distance between points at the center: {results['avg_center_distance']}")
    print(f"Total number of datapoints inside the borders: {results['total_datapoints']}")


def process_gpkg_files(directory):
    """
    Navigate through each subdirectory within the given directory,
    read .gpkg files, and extract coordinates from geometries.
    """
    all_coordinates = []
    all_tiles = []

    # Walk through the directory and its subdirectories
    for subdir, dirs, files in os.walk(directory):
        for file in glob.glob(os.path.join(subdir, '*.gpkg')):
            # Read the GeoPackage file
            print(os.path.join(subdir, '*.gpkg'))
            gdf = gpd.read_file(file)
            # Iterate through geometries in the GeoDataFrame
            for geometry in gdf.geometry:
                all_coordinates.append(geometry.bounds)

        for file in glob.glob(os.path.join(subdir, '*.tif')):
            with Image.open(file) as img:
                # Convert the image to a NumPy array to get pixel data
                pixel_data = np.array(img)
                all_tiles.append(img)

    return all_coordinates, all_tiles


def display_tiles_with_coordinates(tiles_coordinates, tile_images):
    """
    Display each tile image in a separate subplot with coordinates as ticks, including a colorbar
    for the first subplot and suptitle for the entire figure.

    Args:
    tiles_coordinates (list of tuples): Coordinates of the individual tiles.
    tile_images (list of ndarrays): Image data for each tile.

    Each subplot shows the tile image with its actual coordinate bounds labeled on the x and y axes.
    """
    n_tiles = len(tile_images)
    n_cols = int(np.ceil(np.sqrt(n_tiles)))  # Determine the number of columns for the subplot grid
    n_rows = int(np.ceil(n_tiles / n_cols))  # Determine the number of rows for the subplot grid

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, 15), constrained_layout=True)

    if n_tiles == 1:
        axes = [axes]  # Make the single axis iterable
    else:
        axes = axes.flatten()

    for idx, (tile_coord, tile_image) in enumerate(zip(tiles_coordinates, tile_images)):
        ax = axes[idx]

        if not isinstance(tile_image, np.ndarray):
            tile_image = np.array(tile_image, dtype=np.float32)

        im = ax.imshow(tile_image, cmap='Greens', origin="lower")

        # Set the ticks to represent the actual coordinates on the edges of each tile
        ax.set_xticks([0, tile_image.shape[1]])
        ax.set_yticks([0, tile_image.shape[0]])
        ax.set_xticklabels([tile_coord[0], tile_coord[2]])
        ax.set_yticklabels([tile_coord[3], tile_coord[1]])

        ax.set_xlabel("Easting")
        ax.set_ylabel("Northing")
        ax.set_title(f"Tile {idx+1}", color='red', fontsize=18, pad=20)  # Larger font size for the title

    # Add a suptitle for the entire figure
    fig.suptitle('Terrain Altitude Tiles', fontsize=20)

    # Place a colorbar to the left of the first subplot
    if n_tiles > 0:
        fig.colorbar(im, ax=axes[0], fraction=0.046, pad=0.04)

    plt.show()


def assemble_tiles(tiles_coordinates, tile_images):
    """
    Assembles multiple terrain altitude tiles into a single image.

    Args:
    tiles_coordinates (list of tuples): Each tuple contains the (min_x, min_y, max_x, max_y) coordinates of a tile.
    tile_images (list of arrays): Each array is the altitude data for a tile.

    Returns:
    np.ndarray: The assembled full image array of altitude data.
    int: Minimum x coordinate of the assembled image.
    int: Minimum y coordinate of the assembled image.
    int: Maximum x coordinate of the assembled image.
    int: Maximum y coordinate of the assembled image.
    """
    min_x = min(coord[0] for coord in tiles_coordinates)
    min_y = min(coord[1] for coord in tiles_coordinates)
    max_x = max(coord[2] for coord in tiles_coordinates)
    max_y = max(coord[3] for coord in tiles_coordinates)

    full_width = int((max_x - min_x) / 5000) * 5000
    full_height = int((max_y - min_y) / 5000) * 5000

    full_image_array = np.zeros((full_height, full_width), dtype=np.float32)

    for idx, (tile_coord, tile_image) in enumerate(zip(tiles_coordinates, tile_images)):
        paste_x = int((tile_coord[0] - min_x))
        paste_y = int((tile_coord[1] - min_y))

        if not isinstance(tile_image, np.ndarray):
            tile_image_array = np.array(tile_image, dtype=np.float32)
        else:
            tile_image_array = tile_image
        tile_image_array = cv2.flip(tile_image_array, 0)

        full_image_array[paste_y:paste_y + 5000, paste_x:paste_x + 5000] = tile_image_array

    return full_image_array, int(min_x), int(min_y), int(max_x), int(max_y)


def plot_float_array_image(origin, image_array, min_x, min_y, max_x, max_y, tiles_coordinates):
    """
    Plots the assembled image array with annotations for tile numbers and boundary coordinates.

    Args:
    image_array (np.ndarray): The assembled full image array of altitude data.
    min_x, min_y, max_x, max_y (int): Boundaries of the assembled image.
    tiles_coordinates (list of tuples): Coordinates of the individual tiles.
    """
    fig, ax = plt.subplots(figsize=(10, 10))
    cax = ax.imshow(image_array, origin='lower', cmap='Greens')

    fig.colorbar(cax, ax=ax, fraction=0.046, pad=0.04).set_label('Altitude (m)')
    ax.set_title("Assembled Terrain Altitude Map", pad=30)
    ax.set_xlabel("Easting pixel coordinate (origin: tile 2 pixel 0)")
    ax.set_ylabel("Northing pixel coordinate (origin: tile 2 pixel 0)")
    ax.legend(["Tile Boundaries"], loc="upper right")


    tile_number = 1
    for tile_coord in tiles_coordinates:
        paste_x = int((tile_coord[0] - min_x))
        paste_y = int((tile_coord[1] - min_y))

        center_x = paste_x + 2500
        center_y = paste_y + 2500
        ax.text(center_x, center_y, f'Tile {tile_number}', color='red', ha='center', va='center', fontsize=12)
        tile_number += 1

    for x in range(min_x, max_x + 5000, 5000):
        ax.axvline(x=(x - min_x), color='red')
        ax.text(x - min_x - 1330, 16250, f'Easting={x}', color='red', verticalalignment='top', horizontalalignment='left')

    for y in range(min_y, max_y + 5000, 5000):
        adjusted_y = (y - min_y)
        ax.axhline(y=adjusted_y, color='red')
        ax.text(6300, adjusted_y + 200, f'Northing={y}', color='red', horizontalalignment='left', verticalalignment='bottom')

    plt.scatter(origin[0] - min_x, origin[1] - min_y, color="blue", label="Position of the origin")
    plt.tight_layout()
    plt.show()


def get_altitude(northing, easting, altitude_map, min_x, min_y):
    """
    Retrieves the altitude for a given northing and easting coordinate from an altitude map.

    Parameters:
    northing (float): Northing coordinate of the point.
    easting (float): Easting coordinate of the point.
    altitude_map (numpy.ndarray): 2D numpy array representing the altitude map.
    min_x (float): Easting coordinate corresponding to the 0 x pixel of the altitude map.
    min_y (float): Northing coordinate corresponding to the 0 y pixel of the altitude map.

    Returns:
    float: The altitude at the given northing and easting, or None if the point is outside the map.
    """

    # Calculate the pixel coordinates in the altitude map


    pixel_x = int(easting - min_x)
    pixel_y = int(northing - min_y)

    # Check if the calculated pixel coordinates are within the bounds of the altitude map
    if 0 <= pixel_x < altitude_map.shape[1] and 0 <= pixel_y < altitude_map.shape[0]:
        return altitude_map[pixel_y, pixel_x]  # Note: numpy arrays are accessed row-first (y, x)
    else:
        raise Exception("Coordinate does not exist")  # The point is outside the bounds of the altitude map


def sample_altitude(coords, origin, assembled_image, min_x, min_y):
    """
    Sample the altitude for a set of coordinates, offset by an origin, and plot the results in 3D.

    Args:
        coords (list of tuples): List of (easting, northing) coordinates.
        origin (tuple): The (easting, northing) origin to be added to each coordinate.
        assembled_image (np.ndarray): The full altitude image from which altitudes will be sampled.
        min_x (float): The minimum easting value of the altitude image.
        min_y (float): The minimum northing value of the altitude image.

    Returns:
        np.ndarray: An array of (easting, northing, altitude) for the sampled points.
    """
    # Apply the origin offset to each coordinate
    coords_origin = [tuple(map(sum, zip(coord, origin))) for coord in coords]

    # Sample the altitude for each coordinate

    list_xyz = [
        (easting, northing, get_altitude(northing, easting, assembled_image, min_x, min_y))
        for easting, northing in coords_origin
    ]
    list_xyz = np.array(list_xyz)

    # Unpack the list of points into their respective x, y, and z components for plotting
    x, y, z = zip(*list_xyz)

    # Setup the 3D scatter plot
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    ax.scatter(x, y, z, s=10, cmap="Greens", c =z, alpha=0.005)  # Slightly larger dots with edges

    ax.scatter(origin[0], origin[1], 120, color="Black", s=40, label="origin")


    # Set axis labels and the plot title
    ax.set_xlabel('Easting')
    ax.set_ylabel('Northing')
    ax.set_zlabel('Altitude')
    ax.set_title('3D Scatter Plot of Altitude Samples')

    # Set Z-axis limits
    z_min, z_max = 0, 800
    ax.set_zlim(z_min, z_max)
    plt.legend()

    plt.show()
    print("Shape: ", list_xyz.shape)

    return list_xyz
