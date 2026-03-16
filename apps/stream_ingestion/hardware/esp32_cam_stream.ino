#include "esp_camera.h"
#include <WiFi.h>
#include <ArduinoWebsockets.h>
#include <base64.h>

// --- Configuration ---
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Authentication
const char* drone_id = "DRONE_ID";
const char* api_key = "sk_drone_your_api_key_here";

// Backend WebSocket URL
// Format: ws://<BACKEND_IP>:8000/ws/stream/<STREAM_ID>/
const char* websockets_connection_string = "ws://192.168.1.100:8000/ws/stream/your-stream-uuid/";

// ... rest of the pinout remains same ...
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

using namespace websockets;
WebsocketsClient client;

unsigned long last_frame_time = 0;
const int frame_interval = 100; // ms (approx 10 FPS)
int frame_count = 0;
bool is_authenticated = false;

void setup() {
  Serial.begin(115200);
  
  // Camera Config
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  // Frame settings
  if(psramFound()){
    config.frame_size = FRAMESIZE_QVGA; // 320x240 for stability
    config.jpeg_quality = 12;
    config.fb_count = 2;
  } else {
    config.frame_size = FRAMESIZE_QVGA;
    config.jpeg_quality = 12;
    config.fb_count = 1;
  }

  // Init Camera
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return;
  }

  // Connect WiFi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");

  // Connect WebSocket
  client.onMessage([](WebsocketsMessage message) {
    Serial.print("Got Message: ");
    Serial.println(message.data());
    
    // Check for auth success
    if (message.data().indexOf("auth_success") > -1) {
      is_authenticated = true;
      Serial.println("Authentication Successful!");
    } else if (message.data().indexOf("auth_failed") > -1) {
      is_authenticated = false;
      Serial.println("Authentication Failed!");
    }
  });

  client.onEvent([](WebsocketsEvent event, String data) {
    if(event == WebsocketsEvent::ConnectionOpened) {
      Serial.println("WebSocket Connected");
      send_auth();
    } else if(event == WebsocketsEvent::ConnectionClosed) {
      Serial.println("WebSocket Disconnected");
      is_authenticated = false;
    }
  });

  client.connect(websockets_connection_string);
}

void loop() {
  if (client.available()) {
    client.poll();
    
    if (is_authenticated) {
      unsigned long now = millis();
      if (now - last_frame_time > frame_interval) {
        send_frame();
        last_frame_time = now;
      }
    }
  } else {
    Serial.println("Reconnecting WebSocket...");
    is_authenticated = false;
    client.connect(websockets_connection_string);
    delay(2000);
  }
}

void send_auth() {
  String json = "{\"type\":\"authenticate\",\"drone_id\":\"" + String(drone_id) + "\",\"api_key\":\"" + String(api_key) + "\"}";
  client.send(json);
  Serial.println("Sent authentication request");
}

void send_frame() {
  camera_fb_t * fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Camera capture failed");
    return;
  }

  // Convert to Base64
  String encoded = base64::encode(fb->buf, fb->len);
  
  // Create JSON message
  String json = "{\"type\":\"frame_ingestion\",\"frame_data\":\"" + encoded + "\",\"frame_number\":" + String(frame_count++) + "}";
  
  // Send
  client.send(json);
  
  esp_camera_fb_return(fb);
}
