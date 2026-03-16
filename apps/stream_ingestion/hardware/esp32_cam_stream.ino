#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoWebsockets.h>
#include <ArduinoJson.h>
#include <base64.h>

// --- Configuration ---
const char* ssid            = "YOUR_WIFI_SSID";
const char* wifi_password   = "YOUR_WIFI_PASSWORD";
const char* server_ip       = "192.168.1.100";  // Backend server IP
const int   server_port     = 8000;

// Drone Credentials
const char* drone_id  = "DRN-123";
const char* api_key   = "sk_drone_your_api_key_here";

// These are discovered dynamically from /api/v1/streams/config/
String stream_id       = "";
String websocket_url   = "";

// Camera Pinout (AI-Thinker)
#define PWDN_GPIO_NUM  32
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM   0
#define SIOD_GPIO_NUM  26
#define SIOC_GPIO_NUM  27
#define Y9_GPIO_NUM    35
#define Y8_GPIO_NUM    34
#define Y7_GPIO_NUM    39
#define Y6_GPIO_NUM    36
#define Y5_GPIO_NUM    21
#define Y4_GPIO_NUM    19
#define Y3_GPIO_NUM    18
#define Y2_GPIO_NUM     5
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM  23
#define PCLK_GPIO_NUM  22

using namespace websockets;
WebsocketsClient client;

unsigned long last_frame_time = 0;
const int frame_interval   = 100; // ~10 FPS
int  frame_count           = 0;
bool is_authenticated      = false;
bool is_on_patrol          = false; // true only when server sends patrol_started
int  current_patrol_id     = -1;

// ─────────────────────────────────────────────
// Step 0: Discover config from backend
// ─────────────────────────────────────────────
bool discoverConfig() {
  HTTPClient http;
  String url = "http://" + String(server_ip) + ":" + server_port + "/api/v1/streams/config/";
  http.begin(url);
  http.addHeader("X-DRONE-ID", drone_id);
  http.addHeader("X-API-KEY",  api_key);

  int code = http.GET();
  if (code == 200) {
    String body = http.getString();
    StaticJsonDocument<256> doc;
    deserializeJson(doc, body);
    stream_id     = String(doc["stream_id"].as<const char*>());
    websocket_url = String(doc["websocket_url"].as<const char*>());
    Serial.println("Config fetched. Stream ID: " + stream_id);
    http.end();
    return true;
  }
  Serial.println("Config discovery failed: " + String(code));
  http.end();
  return false;
}

// ─────────────────────────────────────────────
// Message handler
// ─────────────────────────────────────────────
void onMessageReceived(WebsocketsMessage msg) {
  StaticJsonDocument<512> doc;
  deserializeJson(doc, msg.data());
  const char* type = doc["type"];

  if (strcmp(type, "auth_success") == 0) {
    is_authenticated = true;
    Serial.println("Auth OK. Waiting for patrol command...");

  } else if (strcmp(type, "auth_failed") == 0) {
    is_authenticated = false;
    Serial.println("Auth FAILED: " + String(doc["message"].as<const char*>()));

  } else if (strcmp(type, "patrol_started") == 0) {
    // Server is starting a patrol — begin streaming
    current_patrol_id = doc["patrol_id"];
    is_on_patrol = true;
    Serial.println("PATROL STARTED! ID=" + String(current_patrol_id) + " — Streaming begins.");

  } else if (strcmp(type, "patrol_ended") == 0) {
    // Server ended patrol — stop streaming
    is_on_patrol = false;
    current_patrol_id = -1;
    Serial.println("PATROL ENDED — Streaming paused.");
  }
}

// ─────────────────────────────────────────────
// Setup
// ─────────────────────────────────────────────
void setup() {
  Serial.begin(115200);

  // Camera init
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;
  config.pin_d0       = Y2_GPIO_NUM;
  config.pin_d1       = Y3_GPIO_NUM;
  config.pin_d2       = Y4_GPIO_NUM;
  config.pin_d3       = Y5_GPIO_NUM;
  config.pin_d4       = Y6_GPIO_NUM;
  config.pin_d5       = Y7_GPIO_NUM;
  config.pin_d6       = Y8_GPIO_NUM;
  config.pin_d7       = Y9_GPIO_NUM;
  config.pin_xclk     = XCLK_GPIO_NUM;
  config.pin_pclk     = PCLK_GPIO_NUM;
  config.pin_vsync    = VSYNC_GPIO_NUM;
  config.pin_href     = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn     = PWDN_GPIO_NUM;
  config.pin_reset    = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size   = FRAMESIZE_QVGA;
  config.jpeg_quality = 12;
  config.fb_count     = psramFound() ? 2 : 1;

  if (esp_camera_init(&config) != ESP_OK) {
    Serial.println("Camera init FAILED");
    return;
  }

  // WiFi
  WiFi.begin(ssid, wifi_password);
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println("\nWiFi OK: " + WiFi.localIP().toString());

  // Discovery
  while (!discoverConfig()) { delay(5000); }

  // WebSocket handlers
  client.onMessage(onMessageReceived);
  client.onEvent([](WebsocketsEvent event, String data) {
    if (event == WebsocketsEvent::ConnectionOpened) {
      Serial.println("WS Connected. Authenticating...");
      String auth = "{\"type\":\"authenticate\",\"drone_id\":\"" + String(drone_id) + "\",\"api_key\":\"" + String(api_key) + "\"}";
      client.send(auth);
    } else if (event == WebsocketsEvent::ConnectionClosed) {
      Serial.println("WS Disconnected.");
      is_authenticated = false;
      is_on_patrol     = false;
    }
  });

  client.connect(websocket_url);
}

// ─────────────────────────────────────────────
// Loop
// ─────────────────────────────────────────────
void loop() {
  if (client.available()) {
    client.poll();

    // Only stream when authenticated AND on an active patrol
    if (is_authenticated && is_on_patrol) {
      unsigned long now = millis();
      if (now - last_frame_time > frame_interval) {
        sendFrame();
        last_frame_time = now;
      }
    }
  } else {
    Serial.println("Reconnecting...");
    is_authenticated = false;
    is_on_patrol     = false;
    delay(3000);
    client.connect(websocket_url);
  }
}

// ─────────────────────────────────────────────
// Send a single JPEG frame
// ─────────────────────────────────────────────
void sendFrame() {
  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) { Serial.println("Frame capture failed"); return; }

  String encoded = base64::encode(fb->buf, fb->len);
  String json = "{\"type\":\"frame_ingestion\","
                "\"frame_data\":\"" + encoded + "\","
                "\"frame_number\":" + String(frame_count++) + "}";
  client.send(json);
  esp_camera_fb_return(fb);
}


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
