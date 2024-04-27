import pyproj
import numpy as np
import pandas as pd
from copy import deepcopy
import matplotlib.pyplot as plt

import utils


###############################
###### PREPROCESSING DF #######
###############################

def rename_columns(df):
    """
    Take the original woodgate data df, rename some columns and returns it
    Make it obvious what each data refers to, formats are added in the name of the column
    coordinates are called WSG84 since we will introduce a OSGB36 version of them later in the code
    """

    df = deepcopy(df)
    # Rename columns to indicate WGS84 where applicable and rename 'Bee' to 'Bee_ID'
    df.rename(columns={
        'FlightNo': "BeeFlightNo",
        'Bee': 'Bee_ID',
        'Time': 'Time (hh:mm:ss)',
        'Latitude': 'Bee_Latitude_WGS84',
        'Longitude': 'Bee_Longitude_WGS84',
        'Radar-Latitude': 'Radar_Latitude_WGS84',
        'Radar-Longitude': 'Radar_Longitude_WGS84',
        'Nest-Latitude': 'Nest_Latitude_WGS84',
        'Nest-Longitude': 'Nest_Longitude_WGS84',
    }, inplace=True)

    return df


def add_first_flight_date(df):
    """
    Group by 'Bee' and find the minimum 'Date' for each group, add the column
    to the original dataframe
    """
    df_copy = deepcopy(df)
    first_flight_dates = df_copy.groupby('Bee_ID')['Date'].min().reset_index()
    first_flight_dates.rename(columns={'Date': 'First_Flight_Date'}, inplace=True)
    df_copy = pd.merge(df_copy, first_flight_dates, on='Bee_ID', how='left')

    return df_copy


def convert_lat_long_to_osgb36(df):
    """
    Converts latitude and longitude columns in the DataFrame to OSGB36 format and adds them as new columns.
    """

    df = deepcopy(df)
    # Define the transformation from WGS84 to OSGB36
    transformer = pyproj.Transformer.from_crs("epsg:4326", "epsg:27700", always_xy=True)

    # Function to apply the transformation and create new columns
    def apply_transformation(row, lat_col, lon_col, new_lat_col, new_lon_col):
        lon, lat = transformer.transform(row[lon_col], row[lat_col])
        df.loc[row.name, new_lat_col] = lat
        df.loc[row.name, new_lon_col] = lon

    # Convert and add new columns for each pair of latitude and longitude columns
    for lat_col, lon_col in [('Bee_Latitude_WGS84', 'Bee_Longitude_WGS84'), ('Radar_Latitude_WGS84', 'Radar_Longitude_WGS84'), ('Nest_Latitude_WGS84', 'Nest_Longitude_WGS84')]:
        new_lat_col = lat_col[:-6] + '_OSGB36'
        new_lon_col = lon_col[:-6] + '_OSGB36'
        df.apply(apply_transformation, axis=1, lat_col=lat_col, lon_col=lon_col, new_lat_col=new_lat_col, new_lon_col=new_lon_col)

    return df


def add_distance_to_nest_column(df):
    """
    Adds a column 'Distance_to_nest' to the DataFrame, representing the distance
    from each point to the nest, both in OSGB36 coordinates.
    """
    df = deepcopy(df)
    # Calculate the Euclidean distance
    df['Distance_to_nest (m)'] = np.sqrt((df['Bee_Latitude_OSGB36'] - df['Nest_Latitude_OSGB36'])**2 + (df['Bee_Longitude_OSGB36'] - df['Nest_Longitude_OSGB36'])**2)

    return df


def add_time_between_steps_column(df):
    """
    Adds a column 'Time_between_steps' indicating the time in seconds between consecutive steps
    within the same flight, taking into account the date and time.
    The first step of each flight has this value set to NaN.
    """
    df = deepcopy(df)

    # Ensure 'Date' and 'Time (hh:mm:ss)' are in string format and combine into a single datetime column
    df['Datetime'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['Time (hh:mm:ss)'].astype(str))

    # Calculate the difference in seconds between consecutive steps within the same flight
    df['Time_between_steps (s)'] = df.groupby(['Bee_ID', 'BeeFlightNo'])['Datetime'].diff().dt.total_seconds()

    # Post-process to set the first timestep of each flight to NaN
    # This uses a more direct approach to identify the first step of each flight
    df['First_Step'] = df.groupby(['Bee_ID', 'BeeFlightNo'])['Datetime'].transform('min')
    df['Time_between_steps (s)'] = np.where(df['Datetime'] == df['First_Step'], np.nan, df['Time_between_steps (s)'])

    # Optional: drop the 'Datetime' and 'First_Step' columns if they're no longer needed
    df.drop(['Datetime', 'First_Step'], axis=1, inplace=True)

    return df


def add_flight_times_columns(df):
    """
    Enhances the DataFrame with additional columns: total time spent in pauses/stops (longer than 3 minutes) during a flight,
    total flight time, total active flight time excluding these pauses, and the ratio of active flight time to total flight time.
    """

    # Ensure not to modify the original DataFrame passed in
    df = df.copy()

    # Calculate the total flight time for each group
    df['Total_Flight_Time'] = df.groupby(['Bee_ID', 'BeeFlightNo'])['Time_between_steps (s)'].transform('sum')

    # Initialize Total_Pause_Time column to 0 for all rows to ensure every group has a value
    df['Total_Pause_Time'] = 0

    # Calculate the total pause time for each group (pauses longer than 3 minutes) and update the DataFrame
    pause_times = df[df['Time_between_steps (s)'] > 180].groupby(['Bee_ID', 'BeeFlightNo'])['Time_between_steps (s)'].sum().reset_index()
    pause_times.rename(columns={'Time_between_steps (s)': 'Total_Pause_Time'}, inplace=True)
    df = pd.merge(df, pause_times, on=['Bee_ID', 'BeeFlightNo'], how='left').fillna(0)

    # If merge creates an additional column for Total_Pause_Time (e.g., Total_Pause_Time_x and Total_Pause_Time_y), adjust accordingly
    if 'Total_Pause_Time_y' in df.columns:
        df['Total_Pause_Time'] = df['Total_Pause_Time_y']
        df.drop(columns=['Total_Pause_Time_x', 'Total_Pause_Time_y'], inplace=True)

    # Calculate the total active flight time excluding pauses for each group
    df['Total_Active_Time'] = df['Total_Flight_Time'] - df['Total_Pause_Time']

    # Calculate the ratio of active time to total flight time for each group
    df['Ratio_Active_Total'] = df['Total_Active_Time'] / df['Total_Flight_Time']

    return df


def add_distance_between_steps_column(df):
    """
    Adds a column 'Distance_between_steps' indicating the Euclidean distance in meters between
    consecutive steps within the same flight based on OSGB36 coordinates. The first step of each
    flight has this value set to NaN.
    """
    # Define a function to calculate Euclidean distance
    def euclidean_distance(x1, y1, x2, y2):
        return np.sqrt((x2 - x1)**2 + (y2 - y1)**2)

    df = deepcopy(df)
    # Calculate distances between consecutive steps within the same flight
    df['Distance_between_steps (m)'] = np.nan  # Initialize column with NaNs
    for (bee, flight), group in df.groupby(['Bee_ID', 'BeeFlightNo']):
        indices = group.index
        latitudes = group['Bee_Latitude_OSGB36'].values
        longitudes = group['Bee_Longitude_OSGB36'].values
        distances = [np.nan] + [euclidean_distance(lat1, lon1, lat2, lon2) for lat1, lon1, lat2, lon2 in zip(latitudes[:-1], longitudes[:-1], latitudes[1:], longitudes[1:])]
        df.loc[indices, 'Distance_between_steps (m)'] = distances

    return df


def add_speed_between_steps_column(df):
    """
    Adds a column 'Speed_between_steps' to the DataFrame indicating the speed in meters per second
    maintained between the last and current coordinate for each timestep within the same flight.
    The first timestep of each flight has this value set to NaN.
    """
    df = deepcopy(df)

    df['Speed_between_steps (m/s)'] = df['Distance_between_steps (m)'] / df['Time_between_steps (s)']

    # Replace infinities with NaN, which can occur if Time_between_steps is zero
    df['Speed_between_steps (m/s)'].replace([np.inf, -np.inf], np.nan, inplace=True)

    # Set the first timestep of each flight to NaN for speed
    df.loc[df.groupby(['Bee_ID', 'BeeFlightNo'])['Time (hh:mm:ss)'].head(1).index, 'Speed_between_steps (m/s)'] = np.nan
    return df


# TODO: It isnt exactly what is written in the paper
def classify_inward_outward_trajectories(df):
    """
    Adds a column 'Trajectory' to the DataFrame indicating whether each row (step) is part of an
    inward (approaching the nest) or outward (moving away from the nest) trajectory.
    """
    df = deepcopy(df)
    # Calculate the change in distance to the nest between consecutive steps within the same flight
    df['Distance_to_nest_change'] = df.groupby(['Bee_ID', 'BeeFlightNo'])['Distance_to_nest (m)'].diff()

    # Classify each step based on the change in distance to the nest
    def classify_trajectory(change):
        if pd.isna(change):  # First step of each flight or missing data
            return "Unknown"
        elif change > 0:
            return "Outward"
        elif change < 0:
            return "Inward"
        else:  # No change in distance
            return "Stationary"

    df['Direction'] = df['Distance_to_nest_change'].apply(classify_trajectory)

    # Drop the temporary 'Distance_to_nest_change' column as it's no longer needed
    df.drop('Distance_to_nest_change', axis=1, inplace=True)

    return df


def sum_and_max(df):
    """
    Compute and add a column for : The full trip covered distance, the mean flight speed,
    the maximum distance to the nest. And the last flight of the bee, where she supposedly died.
    """
    # Make a deep copy of the DataFrame to ensure the original data is not modified
    df_copy = df.copy()

    # Calculate the sum of the distance traveled for each flight
    # note that the distance from the hive to the first step of the flight and
    # from the last step to the hive is not taken into account. Thus it can undershoot
    # the actual distance covered by the bee (see df_copy['Fulltrip_FlightDistance'])
    df_copy['Observed_FlightDistance'] = df_copy.groupby(['Bee_ID', 'BeeFlightNo'])['Distance_between_steps (m)'].transform('sum')

    # Calculate the max distance between the bee and the nest for each flight
    df_copy['Max_Distance_to_Nest'] = df_copy.groupby(['Bee_ID', 'BeeFlightNo'])['Distance_to_nest (m)'].transform('max')

    # compute hive-first step and last step-hive distance
    first_last_distances = df_copy.groupby(['Bee_ID', 'BeeFlightNo']).apply(lambda x: pd.Series({
        'Distance_Nest_to_First': np.sqrt((x.iloc[0]['Bee_Latitude_OSGB36'] - x.iloc[0]['Nest_Latitude_OSGB36'])**2 +
                                 (x.iloc[0]['Bee_Longitude_OSGB36'] - x.iloc[0]['Nest_Longitude_OSGB36'])**2),
        'Distance_Last_to_Nest': np.sqrt((x.iloc[-1]['Bee_Latitude_OSGB36'] - x.iloc[-1]['Nest_Latitude_OSGB36'])**2 +
                                (x.iloc[-1]['Bee_Longitude_OSGB36'] - x.iloc[-1]['Nest_Longitude_OSGB36'])**2)
    })).reset_index()

    df_copy = df_copy.merge(first_last_distances, on=['Bee_ID', 'BeeFlightNo'], how='left')

    # Take into account the hive-first step and last step-hive distance
    df_copy['Fulltrip_FlightDistance'] = df_copy['Observed_FlightDistance'] + df_copy['Distance_Nest_to_First'] + df_copy['Distance_Last_to_Nest']

    df_copy["Mean_Flight_Speed"] =  df_copy['Observed_FlightDistance'] / df_copy['Total_Active_Time']

    # Step 1: Determine the maximum 'BeeFlightNo' for each 'Bee_ID'
    max_flight_no_per_bee = df_copy.groupby('Bee_ID')['BeeFlightNo'].transform('max')

    # Step 2: Mark rows as the last flight by comparing each row's 'BeeFlightNo' against the maximum flight number
    df_copy['Last_Flight'] = df_copy['BeeFlightNo'] == max_flight_no_per_bee

    return df_copy


def add_stops(df):
    """
    Add a column to the DataFrame indicating the total number of stops per flight.
    A stop is considered any record with Time_between_steps > 180 seconds.
    """
    # Calculate the number of stops for each flight based on Time_between_steps
    # Group by Bee_ID and BeeFlightNo, then sum occurrences of Time_between_steps > 180 for each group
    stops_per_flight = df.groupby(['Bee_ID', 'BeeFlightNo'])['Time_between_steps (s)'].apply(lambda x: (x > 180).sum()).reset_index(name='Total_Stops')

    # Merge the stops_per_flight with the original df to add the Total_Stops column
    df = df.merge(stops_per_flight, on=['Bee_ID', 'BeeFlightNo'], how='left')

    return df


def compute_disgressiveness(df):
    """
    Compute how straight is the flight betweem the hive, to a hypothetical stop, to the hive.
    If the fly is purely straight and comes back straight, then disgressiveness is 1
    Any non straight trajectory make the disgressiveness increase.
    """
    # Ensure that the DataFrame is not modified
    df_copy = df.copy()
    # Calculate the disgressiveness
    df_copy['Disgressiveness'] = df_copy['Fulltrip_FlightDistance'] / (2 * df_copy['Max_Distance_to_Nest'])

    return df_copy

# TODO
def classify_flight_type(df):
    """
    Classify each flight as 'Explorative' or 'Other' based on disgressiveness and
    the number of stops. A flight is considered 'Explorative' if its disgressiveness
    is more than 3 and it has 0 stops (inferred from Time_between_steps).
    """
    # Function to determine flight type for each group
    def flight_type(group):

        is_explorative = (group['Disgressiveness'].max() > 3)

        is_last = group['Last_Flight'].iloc[0] == True

        # Return a single label for the whole group
        if is_last:
            return "Last flight"

        return "Explorative" if is_explorative else "Exploitative"

    # Group by Bee_ID and BeeFlightNo, then apply the classification
    flight_types = df.groupby(['Bee_ID', 'BeeFlightNo']).apply(flight_type)

    # Map the flight types back to the original DataFrame
    df['Flight_Type'] = df.apply(lambda row: flight_types[(row['Bee_ID'], row['BeeFlightNo'])], axis=1)

    return df


# TODO
def classify_flight_type_woodgate(df):
    """
    Classify a flight as in the paper from Woodgate.
    """
    pass


def drop_columns(df):
    """
    Applied at the end of the preprocessing, drop gps data, since we will only use OSGB35 format
    """

    df = deepcopy(df)

    df.drop(['X', 'Y'], axis=1, inplace=True)
    df.drop(["Bee_Latitude_WGS84", 'Bee_Longitude_WGS84'], axis=1, inplace=True)
    df.drop(['Radar_Latitude_WGS84', 'Radar_Longitude_WGS84'], axis=1, inplace=True)
    df.drop(['Nest_Latitude_WGS84', 'Nest_Longitude_WGS84'], axis=1, inplace=True)

    return df


###########################################
######## PLOTTING AND EXTRACTION ##########
###########################################

def plot_individual_flights(df, bee_id, rows, cols, easting_boundaries, northing_boundaries):
    """
    Plots individual flights for a specified bee, with some additional statistics for each flight

    Args:
    - df (pd.DataFrame): DataFrame containing the bee flight data.
    - bee_id (int): ID of the bee whose flights to plot.
    - rows (int): Number of rows of plots per figure.
    - cols (int): Number of columns of plots per figure.
    - easting_boundaries (tuple): Tuple of (min, max) for Easting boundaries.
    - northing_boundaries (tuple): Tuple of (min, max) for Northing boundaries.
    """
    # Filter flights for the specified bee
    bee_flights = df[df['Bee_ID'] == bee_id]

    unique_flights = bee_flights['BeeFlightNo'].unique()
    total_plots = rows * cols

    # Calculate the total number of figures needed
    total_figures = np.ceil(len(unique_flights) / total_plots).astype(int)

    # Plotting loop
    for fig_index in range(total_figures):
        fig, axs = plt.subplots(rows, cols, figsize=(5*cols, 5*rows), constrained_layout=True)
        fig.suptitle(f'Bee ID {bee_id}', fontsize=16)

        for ax_index in range(total_plots):
            flight_index = fig_index * total_plots + ax_index
            ax = axs.flatten()[ax_index]

            if flight_index < len(unique_flights):

                flight_no = unique_flights[flight_index]
                flight_df, _ = get_flight_data(bee_flights, bee_id, flight_no)
                coordinates = np.column_stack((flight_df['Bee_Longitude_OSGB36'], flight_df['Bee_Latitude_OSGB36']))
                n_timesteps = len(flight_df)

                nest_positiony, nest_positionx = (df['Nest_Latitude_OSGB36'].iloc[0], df['Nest_Longitude_OSGB36'].iloc[0])
                radar_positiony, radar_positionx = (df['Radar_Latitude_OSGB36'].iloc[0], df['Radar_Longitude_OSGB36'].iloc[0])

                total_time_of_flight = flight_df["Total_Flight_Time"].iloc[0] # flight_df['Time_between_steps (s)'].sum()  # INCORRECT
                observed_distance_of_flight = flight_df['Observed_FlightDistance'].iloc[0] # INCORRECT
                fulltrip_distance_of_flight = flight_df['Fulltrip_FlightDistance'].iloc[0]

                mean_speed_of_flight = flight_df["Mean_Flight_Speed"].iloc[0]
                mean_speed_of_flight_kmh = mean_speed_of_flight * 3.6

                # Filter the DataFrame for stops longer than 3 minutes (180 seconds)
                num_flight_stops = flight_df["Total_Stops"].iloc[0]
                flight_stops = flight_df[flight_df['Time_between_steps (s)'] > 180]


                max_distance_from_nest = flight_df['Max_Distance_to_Nest'].iloc[0]
                flight_type_value = flight_df['Flight_Type'].iloc[0]

                # Extract the full date of the flight
                flight_date = flight_df['Date'].dt.strftime('%Y-%m-%d').iloc[0]

                # The rest remains the same
                first_flight_date = flight_df['First_Flight_Date'].min()

                dayfrom0 = (flight_df['Date'] - first_flight_date).dt.days.iloc[0]

                # Format into a single displaying line with the full date
                formatted_line = f"Flight Date: {flight_date}, Days Since First Flight: {dayfrom0}"
                disgressiveness = flight_df['Disgressiveness'].iloc[0]

                total_pause_time = flight_df["Total_Pause_Time"].iloc[0]
                total_active_time = flight_df["Total_Active_Time"].iloc[0]
                ratio_active_total = flight_df["Ratio_Active_Total"].iloc[0]

                ax.scatter(coordinates[:, 0], coordinates[:, 1], c=range(n_timesteps), cmap="plasma", label=f'Flight {flight_no}', alpha=0.6)
                ax.scatter(nest_positionx, nest_positiony, c='red', marker='o', edgecolors='k', s=100, label='Nest Position', zorder=5)  # Nest on the foreground
                ax.scatter(radar_positionx, radar_positiony, c='green', marker='x', s=100, label='Radar Position')

                for _, stop in flight_stops.iterrows():
                    # Assuming the stops are best represented by their geographical (Latitude, Longitude) location
                    ax.scatter(stop['Bee_Longitude_OSGB36'], stop['Bee_Latitude_OSGB36'], c='blue', marker='x', s=100, label='Location of Stops')


                title = (rf"$\bf{{Flight\ No:\ {flight_no}}}$" + "\n"
                f"{formatted_line}, \n"
                 f"Stops: {num_flight_stops}, \n"
                 f"Mean Speed: {mean_speed_of_flight:.1f} m/s = {mean_speed_of_flight_kmh:.1f} km/h, \n"
                 f"Pause Time: {total_pause_time:.1f} s, \n"
                 f"Active Time: {total_active_time:.1f} s, \n"
                 f"Total Time: {total_time_of_flight:.1f} s, \n"
                 f"Ratio active total: {ratio_active_total:.2f}, \n"
                 f"Distance traveled: {fulltrip_distance_of_flight:.1f} m, \n"
                 f"Max distance from nest: {max_distance_from_nest:.1f} m, \n"
                 f"Flight type (disgressiveness thresholding): {flight_type_value}, \n"
                 #f"Flight type (Woodgate): {flight_type_value_woodgate}, \n"
                 f"Disgressiveness: {disgressiveness:.2},"

                 )
                ax.set_title(title, fontsize=10)
                sm = plt.cm.ScalarMappable(cmap='plasma', norm=plt.Normalize(vmin=0, vmax=n_timesteps))
                cbar = plt.colorbar(sm, ax=ax, label='Time step')
                cbar.set_label('Time step', rotation=270, labelpad=15)
            else:
                ax.axis('off')  # Hide axis if no flight

            # Set consistent boundaries for all plots
            ax.set_xlim(easting_boundaries)
            ax.set_ylim(northing_boundaries)
            ax.ticklabel_format(style='plain', useOffset=False)
            ax.grid(True)

        # Add legend and adjust layout outside the loop
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            fig.legend(handles, labels, loc='upper left', ncol=4)
        plt.show()


def get_flight_data(df, bee_id, flights_no):
    """
    Filters a DataFrame to return data for a specific bee's flight and the complement set.

    Args:
    - df (DataFrame): The DataFrame containing bee flight data.
    - bee_id (int): The ID of the bee.
    - flights_no (int or list of int): The flight number or numbers.

    Returns:
    - DataFrame: A filtered DataFrame containing only the data for the specified bee and flight number(s).
    - DataFrame: A DataFrame containing the data for the specified bee but not for the given flight number(s).
    """
    # Ensure flights_no is a list
    if not isinstance(flights_no, list):
        flights_no = [flights_no]

    # Create a deep copy of the DataFrame to avoid modifying the original data
    df_copy = deepcopy(df)

    # Filter the DataFrame based on Bee_ID and BeeFlightNo for included flights
    included_flights = df_copy[(df_copy['Bee_ID'] == bee_id) & (df_copy['BeeFlightNo'].isin(flights_no))]

    # Filter the DataFrame for excluded flights
    excluded_flights = df_copy[(df_copy['Bee_ID'] == bee_id) & (~df_copy['BeeFlightNo'].isin(flights_no))]

    return included_flights, excluded_flights


def extract_coordinates(data, display=True, save_to=None, removal_distance=2):
    """
    Extracts and displays path coordinates of a specific bee from a DataFrame,
    Display an histogram of the distribution of the bee's distance to the hive
    Saves the data to a CSV file.

    Parameters:
    - data (pd.DataFrame): DataFrame containing bee tracking data.
    - display (bool, optional): If True, visualizes the paths and histogram of distances to the nest.
    - save_to (str, optional): Path to save the CSV file. If None, no file is saved. Defaults to None.

    Returns:
    - np.ndarray: Array of [latitude, longitude, hive latitude, hive longitude] for the specified bee.
    """
    bee_data = data[data["Distance_to_nest (m)"] > removal_distance]

    # Extract latitude, longitude, and distance to nest
    latitudes = bee_data['Bee_Latitude_OSGB36'].to_numpy()
    longitudes = bee_data['Bee_Longitude_OSGB36'].to_numpy()
    distances = bee_data['Distance_to_nest (m)'].to_numpy()

    # Assume hive position is constant; take the first entry
    hive_lat = data['Nest_Latitude_OSGB36'].iloc[0]
    hive_lon = data['Nest_Longitude_OSGB36'].iloc[0]

    # Create a 2D array of coordinates
    coordinates = np.column_stack((latitudes, longitudes, np.full(latitudes.shape, hive_lat), np.full(longitudes.shape, hive_lon)))

    if display:
        plt.figure(figsize=(15, 6))

        # Plot coordinates
        plt.subplot(1, 2, 1)
        plt.scatter(longitudes, latitudes, c='blue', marker='o', label=f'Selected coordinates')
        plt.scatter(hive_lon, hive_lat, c='red', marker='x', s=100, label='Hive Position')
        plt.title(f'Selected coordinates and Hive Location', size=20)
        plt.xlabel('Longitude', size=20)
        plt.ylabel('Latitude', size=20)
        plt.tick_params(labelsize=15)
        plt.legend(fontsize=16)
        plt.grid(True)

        # Plot histogram of distances to nest
        plt.subplot(1, 2, 2)
        plt.hist(distances, bins=20, color='green', edgecolor='black')
        plt.title(f'Distribution of Distances to Nest', size=20)
        plt.xlabel('Distance to Nest (m)', size=20)
        plt.ylabel('Sample Count', size=20)
        plt.tick_params(labelsize=15)
        plt.grid(True)

        plt.tight_layout()
        plt.show()

    # Save coordinates to CSV, if a path is provided
    if save_to:
        coord_df = pd.DataFrame(coordinates, columns=['Easting', 'Northing', 'Hive Easting', 'Hive Northing'])
        coord_df.to_csv(save_to, index=False)
        print(f'Coordinates and hive position saved to {save_to}')

    return coordinates
