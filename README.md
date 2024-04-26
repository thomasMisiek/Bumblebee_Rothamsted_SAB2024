# Insect-Based Navigation Model Repository

## Overview
This repository hosts the implementation and results of the study titled "Insect-based navigation model allows efficient long-range visual homing in a 3D simulated environment." The study investigates the visual homing capabilities of a simple navigation model using snapshots,  a mechanism inspired from the ant navigation literature. The research was conducted using a detailed 3D simulation of the Rothamsted Research Center.

## Key Features
- **Simulation of Insect Vision**: We use a large 6 square kilometers 3D model to render 360 degrees panoramic views, of the Rothamsted Research Center, at any altitude and coordimates.
- **Snapshot-Based Navigation**: We Implements an algorithm inspired by the navigation strategies of hymenoptera, focusing on route knowledge rather than mental maps.

## Results
The study highlights:
- Visual homing is facilitated by flying higher.
- Very few cross-altitude generalization, indicating the need for altitude-specific training.
- Insights into potential real-world applications and improvements for aerial navigation systems.
- Hypotheses for the exploration flights and homing of Bumblebees and Honeybees.

## Usage
Details on how to set up and run the simulation are provided in the `docs` folder. This includes environment setup, execution instructions, and configuration options.

## Data
The repository includes:
- Aerial imagery and derived 3D models of Rothamsted Research Center.
- Flight data of insects used for training and testing the navigation model.

The meshes and textures of the reconstructed 3D model of the Rothamsted Research center can be found on a figshare repository:

## Dependencies
- Python 3.8+
- Libraries: NumPy, OpenCV for image processing, and other required packages listed in `requirements.txt`.

## Installation
To set up the simulation environment:

git clone https://github.com/thomasMisiek/Bumblebee_Rothamsted_SAB2024.git
cd Bumblebee_Rothamsted_SAB2024
pip install -r requirements.txt

OR

conda env create -f environment.yml
conda activate Bumblebee_Rothamsted_SAB2024


## Contributors
- Thomas Misiek
- James Knight
- Andrew Philippides

## Citation
If you use the data or algorithms in this study, please cite:

@article{Misiek2024insect,
title={Insect-based navigation model allows efficient long-range visual homing in a 3D simulated environment},
author={Thomas Misiek and Andrew Philippides and James Knight},
journal={Journal of Computational Ethology},
year={2024},
publisher={Springer}
}


## Contact
For any additional questions or requests, please contact [t.misiek@sussex.ac.uk](mailto:t.misiek@sussex.ac.uk).
