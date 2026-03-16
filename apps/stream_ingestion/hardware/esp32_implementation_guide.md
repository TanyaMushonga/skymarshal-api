# ESP32-CAM Implementation Guide for Sky Marshal

This guide outlines how to configure and program an ESP32-CAM module to stream live video to the Sky Marshal backend via WebSockets.

## 📋 Prerequisites

- **Hardware**: ESP32-CAM (AI-Thinker model recommended).
- **Libraries**:
    - `WiFi.h` (Built-in)
    - `ArduinoWebsockets` (by Gil Maimon)
    - `base64` (Built-in or standard library)

## 📡 Connection Workflow

The ESP32-CAM follows a strict communication protocol to ensure security and performance.

### 0. Discovery (Recommended)
Before connecting to the WebSocket, the ESP32 can request its dynamic configuration (like the `stream_id` and correct `websocket_url`) using a simple HTTP GET request.

**Endpoint**: `GET /api/v1/streams/config/`  
**Headers**:
- `X-DRONE-ID`: Your Drone ID (e.g., `DRN-123`)
- `X-API-KEY`: Your secret API key

**Example Response**:
```json
{
  "stream_id": "f47...d479",
  "drone_id": "DRN-123",
  "websocket_url": "ws://192.168.1.100:8000/ws/stream/f47...d479/"
}
```

### 1. Establish WebSocket Connection
Connect to the server using the `websocket_url` obtained in the discovery step (or the manually provided URL).
`ws://<SERVER_IP>:8000/ws/stream/<STREAM_ID>/`

> [!IMPORTANT]
> The `STREAM_ID` is a unique UUID found in your Drone Details dashboard or via the `/api/v1/streams/` endpoint.

### 2. Authenticate
Immediately after connecting, send an authentication JSON. If this step is skipped, the server will drop the connection.

**Request Structure:**
```json
{
  "type": "authenticate",
  "drone_id": "DRN-123",
  "api_key": "sk_drone_your_secret_key_here"
}
```

### 3. Stream Frames
Once the server responds with `{ "type": "auth_success" }`, start sending video frames as Base64 strings.

**Request Structure:**
```json
{
  "type": "frame_ingestion",
  "frame_data": "base64_encoded_jpeg_string",
  "frame_number": 1,
  "timestamp": "2024-03-16T12:34:56.789Z"
}
```

---

## 💻 Example Arduino Code Snippet

Below is the core logic for the authentication and frame transmission.

```cpp
#include <ArduinoWebsockets.h>
#include <base64.h>

using namespace websockets;
WebsocketsClient client;
bool is_authenticated = false;

// Call this immediately after WebSocket is connected
void send_auth() {
  String json = "{\"type\":\"authenticate\",\"drone_id\":\"DRN-123\",\"api_key\":\"sk_drone_...\"}";
  client.send(json);
}

// Call this in your loop to stream frames
void send_frame(camera_fb_t * fb) {
  if (!is_authenticated || !fb) return;

  // Convert JPEG to Base64
  String encoded = base64::encode(fb->buf, fb->len);
  
  // Build and send JSON
  String json = "{\"type\":\"frame_ingestion\",\"frame_data\":\"" + encoded + "\"}";
  client.send(json);
}
```

## ⚙️ Optimization Tips

1. **Resolution**: Use `FRAMESIZE_QVGA` (320x240) or `FRAMESIZE_CIF` (400x296) for the best balance between quality and transmission speed.
2. **Frame Rate**: Aim for 10-15 FPS. Higher rates may cause buffer overflows on the ESP32.
3. **JPEG Quality**: Setting `jpeg_quality` between 10 and 12 provides good compression without excessive artifacts.
