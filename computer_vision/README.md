# SkyMarshal: Intelligent Aerial Traffic Observation System

SkyMarshal is a computer-vision-based traffic monitoring system designed to detect vehicles, track their movement across frames, and provide real-time speed estimation and Automatic License Plate Recognition (ALPR). This system is optimized for aerial or high-angle surveillance footage.

## Features

- **Vehicle Detection and Tracking**: Utilizes YOLOv8 and BoT-SORT for robust identification and tracking of cars, trucks, motorcycles, and buses.
- **Automatic License Plate Recognition (ALPR)**: Integrated secondary detection model for license plate localization followed by Optical Character Recognition (OCR) using EasyOCR.
- **Speed Estimation**: Employs perspective transformation to map image coordinates to real-world metric distances, facilitating accurate speed calculations.
- **Stream Processing**: Optimized for both video file processing and potential expansion to live RTSP streams.

## Project Lifecycle

### 1. Data Acquisition and Preparation

To achieve high accuracy in License Plate Recognition, it is recommended to use specialized datasets.

- **Sourcing Data**: Datasets can be acquired from platforms such as [Roboflow Universe](https://universe.roboflow.com/search?q=license+plate). Search for datasets specifically labelled in YOLOv8 format.
- **Annotation**: If using custom footage, tools like Roboflow can be used to manually annotate license plates. Annotate with a single class: `license-plate`.

### 2. Model Training on Google Colab

Training deep learning models locally can be resource-intensive. Using Google Colab is recommended for its free GPU access.

#### Environment Setup

```python
!pip install ultralytics
```

#### Training Execution

```python
from ultralytics import YOLO

# Initialize with a pre-trained nano model for efficiency
model = YOLO('yolov8n.pt')

# Execute training for 50 epochs
model.train(data='data.yaml', epochs=50, imgsz=640)
```

#### Evaluation

After training, evaluate the performance by reviewing the generated metrics:

- **Accuracy Graphs**: Monitor `results.png` to ensure Loss is decreasing and Mean Average Precision (mAP) is increasing.
- **Visual Validation**: Examine `val_batch0_labels.jpg` to verify detection quality on validation data.

### 3. Deployment and Installation

#### Prerequisites

- Python 3.8 or higher
- A virtual environment (venv) is strongly recommended

#### Installation Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/TanyaMushonga/SkyMarshal.git
   cd SkyMarshal
   ```
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

#### Model Implementation

1. The system automatically utilizes `yolov8n.pt` for general vehicle detection.
2. For ALPR, place your trained model weights (e.g., `best.pt` from your Colab training) into the project root directory.

### 4. Running the System

To process a video file, ensure it is located in the project directory and execute:

```bash
python main.py
```

Output results, including processed videos with bounding boxes, speeds, and identified plates, will be saved in the `output/` directory.

## Project Structure

- `main.py`: Primary execution script.
- `src/`:
  - `detector.py`: Core vehicle detection logic.
  - `processor.py`: Stream management and visualization routines.
  - `speed_estimator.py`: Geometric calculations for speed estimation.
  - `alpr.py`: Specialized module for license plate recognition.
- `output/`: Storage for processed output files.

## License

Distributed under the MIT License. See `LICENSE` for further details.

## Contributing

Contributions are welcome. Please refer to `CONTRIBUTING.md` for submission guidelines.
