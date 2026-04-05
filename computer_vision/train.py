"""
SkyMarshal IATOS — YOLOv8 Training Pipeline
============================================

Steps this script performs:
  1. Extract frames from traffic_sample.mp4
  2. Auto-label frames using yolov8n.pt (pseudo-labelling)
  3. Build a YOLO dataset (images/ + labels/ + dataset.yaml)
  4. Fine-tune YOLOv8 on that dataset
  5. Real PR Curve, Loss Curves, mAP, Confusion Matrix are saved
     in  computer_vision/runs/detect/skymarshal_v1/

Usage (from the repo root, with the venv active):
  python computer_vision/train.py

Dependencies:
  pip install ultralytics opencv-python-headless torch torchvision
"""

import cv2
import os
import random
import shutil
import yaml
from pathlib import Path
from ultralytics import YOLO

# ─── Paths ───────────────────────────────────────────────────────────────────
CV_DIR   = Path(__file__).parent.resolve()
VIDEO    = CV_DIR / "traffic_sample.mp4"
BASE_PT  = CV_DIR / "yolov8n.pt"
DATASET  = CV_DIR / "dataset"
RUNS_DIR = CV_DIR / "runs"

# ─── Dataset settings ────────────────────────────────────────────────────────
FRAME_SKIP      = 10      # extract every Nth frame (lower = more frames, slower)
MAX_FRAMES      = 800     # cap total extracted frames
VAL_SPLIT       = 0.15    # 15 % of frames go to validation
CONF_THRESHOLD  = 0.45    # min confidence for auto-label to count as ground truth
IMG_SIZE        = 640     # YOLO input resolution

# ─── COCO → SkyMarshal class mapping ─────────────────────────────────────────
# Only keep vehicle-relevant COCO classes and remap to compact IDs.
COCO_TO_SKYMARSHAL = {
    2:  (0, "car"),
    3:  (1, "motorcycle"),
    5:  (2, "bus"),
    7:  (3, "truck"),
    0:  (4, "person"),   # pedestrian
}
CLASS_NAMES = [name for _, (_, name) in sorted(COCO_TO_SKYMARSHAL.items(), key=lambda x: x[1][0])]
# Sorted by new id: {0: car, 1: motorcycle, 2: bus, 3: truck, 4: person}
CLASS_NAMES = ["car", "motorcycle", "bus", "truck", "person"]

# ─── Training hyper-parameters ────────────────────────────────────────────────
EPOCHS      = 50        # enough epochs for meaningful curves on a small dataset
BATCH_SIZE  = 16
LR0         = 0.01
PROJECT     = str(RUNS_DIR)
RUN_NAME    = "skymarshal_v1"


def extract_frames(video_path: Path, out_dir: Path, frame_skip: int, max_frames: int) -> list[Path]:
    """Extract every `frame_skip`-th frame from the video, up to max_frames."""
    out_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video_path))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps          = cap.get(cv2.CAP_PROP_FPS)
    duration     = total_frames / fps if fps > 0 else 0

    print(f"[1/4] Video: {total_frames} frames  |  {fps:.1f} FPS  |  {duration:.1f}s")

    extracted = []
    idx = 0
    saved = 0
    while cap.isOpened() and saved < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        if idx % frame_skip == 0:
            img_path = out_dir / f"frame_{saved:05d}.jpg"
            cv2.imwrite(str(img_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
            extracted.append(img_path)
            saved += 1
        idx += 1

    cap.release()
    print(f"    Extracted {len(extracted)} frames → {out_dir}")
    return extracted


def autolabel(frames: list[Path], model: YOLO, labels_dir: Path):
    """
    Run inference on extracted frames and write YOLO-format .txt label files.
    Only write detections for classes that exist in COCO_TO_SKYMARSHAL.
    """
    labels_dir.mkdir(parents=True, exist_ok=True)
    print(f"[2/4] Auto-labelling {len(frames)} frames …")

    total_boxes = 0
    for img_path in frames:
        results = model.predict(str(img_path), conf=CONF_THRESHOLD, verbose=False)[0]
        label_path = labels_dir / (img_path.stem + ".txt")

        lines = []
        for box in results.boxes:
            coco_cls = int(box.cls.item())
            if coco_cls not in COCO_TO_SKYMARSHAL:
                continue
            new_cls, _ = COCO_TO_SKYMARSHAL[coco_cls]
            # box.xywhn → normalised cx, cy, w, h
            cx, cy, w, h = box.xywhn[0].tolist()
            lines.append(f"{new_cls} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")

        label_path.write_text("\n".join(lines))
        total_boxes += len(lines)

    print(f"    Wrote {total_boxes} bounding boxes across {len(frames)} label files")


def build_dataset(frames: list[Path], raw_labels: Path, dataset_root: Path, val_split: float):
    """
    Organise frames + labels into:
      dataset/
        images/train/   images/val/
        labels/train/   labels/val/
    """
    if dataset_root.exists():
        shutil.rmtree(dataset_root)

    for split in ["train", "val"]:
        (dataset_root / "images" / split).mkdir(parents=True)
        (dataset_root / "labels" / split).mkdir(parents=True)

    # Only keep frames that have at least one detection
    valid_frames = [f for f in frames if (raw_labels / (f.stem + ".txt")).read_text().strip() != ""]
    print(f"[3/4] {len(valid_frames)} frames have detections (dropped {len(frames) - len(valid_frames)} empty)")

    random.shuffle(valid_frames)
    split_idx  = int(len(valid_frames) * (1 - val_split))
    train_imgs = valid_frames[:split_idx]
    val_imgs   = valid_frames[split_idx:]

    def copy_pair(img_path: Path, split: str):
        shutil.copy(img_path, dataset_root / "images" / split / img_path.name)
        lbl_path = raw_labels / (img_path.stem + ".txt")
        shutil.copy(lbl_path, dataset_root / "labels" / split / (img_path.stem + ".txt"))

    for f in train_imgs:
        copy_pair(f, "train")
    for f in val_imgs:
        copy_pair(f, "val")

    print(f"    Train: {len(train_imgs)}  |  Val: {len(val_imgs)}")

    # Write dataset.yaml
    yaml_data = {
        "path"   : str(dataset_root.resolve()),
        "train"  : "images/train",
        "val"    : "images/val",
        "nc"     : len(CLASS_NAMES),
        "names"  : CLASS_NAMES,
    }
    yaml_path = dataset_root / "dataset.yaml"
    with open(yaml_path, "w") as f:
        yaml.dump(yaml_data, f, default_flow_style=False)

    print(f"    dataset.yaml written → {yaml_path}")
    return yaml_path


def train(yaml_path: Path):
    """Fine-tune YOLOv8n and produce real evaluation plots."""
    print(f"[4/4] Training YOLOv8n for {EPOCHS} epochs …")
    model = YOLO(str(BASE_PT))
    results = model.train(
        data        = str(yaml_path),
        epochs      = EPOCHS,
        imgsz       = IMG_SIZE,
        batch       = BATCH_SIZE,
        lr0         = LR0,
        project     = PROJECT,
        name        = RUN_NAME,
        exist_ok    = True,
        plots       = True,   # << generates PR_curve, F1_curve, confusion_matrix, results.png
        save        = True,
        val         = True,
        workers     = 4,
        verbose     = True,
    )

    run_dir = Path(PROJECT) / RUN_NAME
    print("\n" + "═" * 60)
    print("✅  Training complete!")
    print(f"    Run dir  : {run_dir}")
    print("    Graphs saved:")
    for plot in ["PR_curve.png", "F1_curve.png", "results.png", "confusion_matrix.png"]:
        p = run_dir / plot
        if p.exists():
            print(f"      • {p}")
    print("═" * 60 + "\n")
    return run_dir


if __name__ == "__main__":
    random.seed(42)

    # Temp dir for raw (pre-split) frames and labels
    raw_frames_dir = CV_DIR / "_raw_frames"
    raw_labels_dir = CV_DIR / "_raw_labels"

    # 1. Extract frames
    frames = extract_frames(VIDEO, raw_frames_dir, FRAME_SKIP, MAX_FRAMES)

    # 2. Load model and auto-label
    print(f"\n    Loading base model: {BASE_PT}")
    model = YOLO(str(BASE_PT))
    autolabel(frames, model, raw_labels_dir)

    # 3. Build train/val dataset
    yaml_path = build_dataset(frames, raw_labels_dir, DATASET, VAL_SPLIT)

    # 4. Train and generate plots
    run_dir = train(yaml_path)

    # Cleanup temp dirs
    shutil.rmtree(raw_frames_dir, ignore_errors=True)
    shutil.rmtree(raw_labels_dir, ignore_errors=True)
    print("    Cleaned up temp directories.")
