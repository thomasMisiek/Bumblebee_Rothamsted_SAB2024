import pandas as pd


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
