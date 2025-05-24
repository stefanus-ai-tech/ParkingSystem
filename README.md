# ParkingSystem

This repository contains a Parking System application that leverages image recognition to manage vehicle entry and exit. It includes a web interface for interaction and backend logic for processing vehicle data.

## Features

- **Vehicle In/Out Management**: Handles the entry and exit of vehicles.
- **Image Recognition**: Utilizes image processing to identify vehicles (cars and motorcycles), likely for license plate recognition or vehicle type classification.
- **Data Storage**: Stores parking-related data.
- **Web Interface**: Provides a user-friendly web interface for system interaction or monitoring.
- **Accuracy Helper**: Tools for evaluating and improving the accuracy of the image recognition models.
- **Labeling Tools**: Utilities for labeling image datasets.

## Technologies Used

- **Python**: Backend logic, image processing, and data management.
- **HTML, CSS, JavaScript**: Frontend web interface.
- **Machine Learning/Computer Vision Libraries**: (Inferred from `choosenCar/`, `choosenMotorCycle/`, `labels.json`, `accuracy_helper.py`, `labeling.py`) Likely uses libraries for image recognition tasks.
- **JSON**: For data storage (`parking_data.json`, `labels.json`).

## Setup

1.  **Install Python dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
2.  **Configure environment variables**:
    Create a `.env` file and add necessary configurations (e.g., API keys, database connections).
3.  **Prepare image datasets**:
    Ensure `choosenCar/` and `choosenMotorCycle/` directories contain the necessary images and `labels.json` files for the image recognition component.

## Usage

To run the application, execute the `main.py` script. The web interface will be accessible via your browser.

```bash
python main.py
```
