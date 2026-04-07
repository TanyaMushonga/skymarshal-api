# Technical Implementation: Patrol & Video Ingestion Workflow

This document outlines the end-to-end technical lifecycle of a patrol session, from the officer's initiation to the delivery of the AI-annotated live feed.

---

## 🚀 1. Patrol Initiation (Activation Phase)

### Step 1.1: Officer Starts Patrol
*   **Actor**: Mobile/Web App
*   **Action**: `POST /api/v1/patrols/start/`
*   **Payload**:
    ```json
    {
      "drone_id": "DRN-123",
      "config": { "sensitivity": "high" }
    }
    ```
*   **Response**: `201 Created`
    ```json
    { "id": "patrol-uuid-here", "status": "ACTIVE", "drone": "DRN-123" }
    ```
*   **Side Effect**: Django clears the `active_patrol_DRN-123` cache.

---

## 📡 2. Device Handshake (Discovery Phase)

### Step 2.1: ESP32 Fetches Configuration
*   **Actor**: ESP32-CAM Firmware
*   **Action**: `GET /api/v1/streams/config/?drone_id=DRN-123` (Polling every 10s)
*   **Internal Response**: `200 OK`
    ```json
    {
      "is_active": true,
      "stream_id": "stream-uuid-here",
      "patrol_id": "patrol-uuid-here",
      "drone_id": "DRN-123",
      "drone_name": "Drone Alpha",
      "websocket_url": "ws://server/ws/stream/stream-uuid/"
    }
    ```
*   **Outcome**: ESP32 transitions from **IDLE** to **STREAMING**.

---

## 🖼️ 3. Data Ingestion (Transmission Phase)

### Step 3.1: Raw Frame Upload
*   **Actor**: ESP32-CAM
*   **Action**: `POST http://ingestion-gateway:3003/api/v1/ingest`
*   **Payload**:
    ```json
    {
      "drone_id": "DRN-123",
      "stream_id": "stream-uuid-here",
      "patrol_id": "patrol-uuid-here",
      "frame_data": "/9j/4AAQSkZJRg...", // Base64 JPEG
      "frame_number": 105,
      "timestamp": 1712487600000,
      "gps": { "lat": -1.2833, "lng": 36.8167 }
    }
    ```
*   **Response**: `202 Accepted`
*   **Ingestion Logic**: Express Gateway validates the payload and pushes it to **Kafka** topic: `raw_video_frames`.

---

## 🧠 4. AI Processing (Inference Phase)

### Step 4.1: Computer Vision Inference
*   **Actor**: CV Service (Python/YOLOv8)
*   **Input**: Kafka `raw_video_frames`
*   **Process**:
    1.  Decodes Base64 JPEG.
    2.  Runs YOLO inference (Vehicle Detection).
    3.  Annotates frame (Draws Bounding Boxes).
    4.  Propagates `patrol_id` metadata.
*   **Outputs**:
    *   **Kafka Topic** `detection_events`: Detections for DB persistence.
    *   **Kafka Topic** `processed_frames`: Annotated frames for live view.

---

## 🌉 5. Real-Time Bridge (Delivery Phase)

### Step 5.1: Persistence
*   **Actor**: Detection Consumer (Django)
*   **Action**: Consumes `detection_events` from Kafka.
*   **Logic**: `Detection.objects.update_or_create(patrol_id=msg.patrol_id, ...)`

### Step 5.2: WebSocket Broadcast
*   **Actor**: Stream Bridge (Django)
*   **Action**: Consumes `processed_frames` from Kafka.
*   **Logic**:
    1.  Automatically upserts `StreamSession` for metadata tracking.
    2.  Broadcasts payload to Django Channels group `live_stream_<stream_id>`.
*   **Actor**: Mobile/Web App
*   **Action**: Subscribed to `ws://server:8000/ws/stream/<stream_id>/`.
*   **Received Message**:
    ```json
    {
       "type": "stream_frame",
       "frame_data": "/9j/ProcessedBase64...",
       "frame_number": 105,
       "patrol_id": "patrol-uuid-here"
    }
    ```

---

## 🛑 6. Patrol Termination (Cleanup Phase)

### Step 6.1: Officer Ends Patrol
*   **Actor**: Mobile/Web App
*   **Action**: `POST /api/v1/patrols/{id}/end/`
*   **Backend Steps**:
    1.  `Patrol.status = 'COMPLETED'`.
    2.  `StreamSession.end_time = now()`.
    3.  Clears `active_patrol_DRN-123` cache.
*   **Device Sync**: ESP32 polls `/config/` within 10s → Receives `{is_active: false}` → Stops streaming immediately.
