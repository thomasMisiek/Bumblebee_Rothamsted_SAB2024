import numpy as np
import pandas as pd
from pyproj import Proj, transform
import plotly.graph_objects as go
import plotly.io as pio

#########################
####### READING #########
#########################

def read_excel_to_dataframe(file_path):
    """
    Reads an Excel file and returns its contents as a pandas DataFrame.

    Args:
    - file_path (str): The path to the Excel (.xlsx) file.

    Returns:
    - pd.DataFrame: The contents of the Excel file as a DataFrame.
    """

    try:
        df = pd.read_excel(file_path, engine='openpyxl')
        return df
    except Exception as e:
        print(f"Error reading the Excel file: {e}")
        return None


def wgs84_to_osgb36(lon, lat):
    """
    Convert WGS84 coordinates to OSGB36.

    Args:
        lon (float): Longitude in WGS84.
        lat (float): Latitude in WGS84.

    Returns:
        tuple: Converted coordinates (longitude, latitude) in OSGB36.
    """
    # Define the projection for WGS84 and OSGB36
    wgs84 = Proj('epsg:4326')
    osgb36 = Proj('epsg:27700')

    # Transform the coordinates
    x, y = transform(wgs84, osgb36, lon, lat)

    return x, y


def osgb36_to_wgs84(x, y):
    """
    Convert OSGB36 coordinates to WGS84.

    Args:
        x (float): Easting in OSGB36.
        y (float): Northing in OSGB36.

    Returns:
        tuple: Converted coordinates (longitude, latitude) in WGS84.
    """
    # Define the projection for OSGB36 and WGS84
    osgb36 = Proj('epsg:27700')
    wgs84 = Proj('epsg:4326')

    # Transform the coordinates
    lon, lat = transform(osgb36, wgs84, x, y)

    return lon, lat


def compare_map(world1, world2):
    """
    Display a 3D scatter plot of two worlds with points colored based on their z-coordinate.

    Parameters:
    - world1, world2: Arrays representing two sets of 3D coordinates (x, y, z).
    """
    # Randomly sample 100000 points from each world to reduce plotting load
    world1_sampled = world1[np.random.choice(world1.shape[0], size=100000, replace=False)]
    world2_sampled = world2[np.random.choice(world2.shape[0], size=100000, replace=False)]

    # Prepare data for plotting
    trace_inside = go.Scatter3d(
        x=world1_sampled[:, 0], y=world1_sampled[:, 1], z=world1_sampled[:, 2],
        mode='markers',
        marker=dict(size=2, color=world1_sampled[:, 2], colorscale='Reds', showscale=False),
        name='Inside'
    )

    trace_outside = go.Scatter3d(
        x=world2_sampled[:, 0], y=world2_sampled[:, 1], z=world2_sampled[:, 2],
        mode='markers',
        marker=dict(size=2, color=world2_sampled[:, 2], colorscale='Greens', showscale=False),
        name='Outside'
    )

    # Initialize and configure the plot
    fig = go.Figure(data=[trace_inside, trace_outside])

    fig.update_layout(
        scene=dict(
            xaxis=dict(title='X Axis'),
            yaxis=dict(title='Y Axis'),
            zaxis=dict(title='Z Axis', range=[-620, 700])
        ),
        width=2000,
        height=1200,
        showlegend=False
    )

    # Set default renderer to 'iframe' for compatibility, show the plot
    pio.renderers.default = 'browser'
    #pio.renderers.default = 'iframe'
    fig.show()
