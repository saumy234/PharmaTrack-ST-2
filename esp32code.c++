// Include necessary libraries
// #include <WiFi.h>
// #include <HTTPClient.h>
// #include <OneWire.h>
// #include <DallasTemperature.h>
// #include <ArduinoJson.h>
// =========================================================
// WIFI CONFIGURATION
// =========================================================

// const char* ssid = "saumya"; // YOUR WIFI SSID
// const char* password = "mylove1500"; // YOUR WIFI PASSWORD

// // =========================================================
// // BACKEND URL
// // =========================================================

// // IMPORTANT: Replace this with your laptop's current local IP address
// // You can find it by running 'ipconfig' in CMD and looking for 'IPv4 Address'
// const char* serverUrl = "http://10.206.242.5:5001/temperature";

// // =========================================================
// // PIN DEFINITIONS
// // =========================================================

// #define ONE_WIRE_BUS 19
// #define LED_PIN 18

// // =========================================================
// // SENSOR SETUP
// // =========================================================

// OneWire oneWire(ONE_WIRE_BUS);
// DallasTemperature sensors(&oneWire);

// // =========================================================
// // TEMPERATURE THRESHOLD (Synced with Backend)
// // =========================================================

// float threshold = 28.0; 

// // =========================================================
// // SETUP
// // =========================================================

// void setup() {
//   Serial.begin(115200);
//   delay(1000);

//   Serial.println("\n--- MediGuard ESP32 Booting ---");



//   pinMode(LED_PIN, OUTPUT);
//   digitalWrite(LED_PIN, LOW);

//   sensors.begin();

//   // CONNECT TO WIFI
//   Serial.printf("Connecting to %s ", ssid);
//   WiFi.begin(ssid, password);

//   int attemptCount = 0;
//   while (WiFi.status() != WL_CONNECTED && attemptCount < 20) {
//     delay(500);
//     Serial.print(".");
//     attemptCount++;
//   }

//   if (WiFi.status() == WL_CONNECTED) {
//     Serial.println("\n[SUCCESS] WiFi Connected!");
//     Serial.print("[INFO] ESP32 IP Address: ");
//     Serial.println(WiFi.localIP());
//   } else {
//     Serial.println("\n[ERROR] WiFi Connection Failed. Check SSID/Password.");
//   }
// }

// // =========================================================
// // MAIN LOOP
// // =========================================================

// void loop() {
//   if (WiFi.status() != WL_CONNECTED) {
//     Serial.println("[WARNING] WiFi lost. Reconnecting...");
//     WiFi.reconnect();
//     delay(2000);
//     return;
//   }

//   // READ TEMPERATURE
//   sensors.requestTemperatures();
//   float temperatureC = sensors.getTempCByIndex(0);

//   Serial.print("\n[SENSOR] Temp: ");
//   Serial.print(temperatureC);
//   Serial.println(" °C");

//   // ALERT LOGIC
//   if (temperatureC > threshold) {
//     digitalWrite(LED_PIN, HIGH);
//     Serial.println("[ALERT] HIGH TEMPERATURE DETECTED!");
//   } else {
//     digitalWrite(LED_PIN, LOW);
//     Serial.println("[INFO] Temperature Normal");
//   }

//   // SEND DATA
//   HTTPClient http;
  
//   Serial.print("[HTTP] Connecting to: ");
//   Serial.println(serverUrl);
  
//   http.begin(serverUrl);
//   http.addHeader("Content-Type", "application/json");

//   // CREATE JSON
//   StaticJsonDocument<200> doc;
//   doc["device_id"] = "ESP32_ROOM_1";
//   doc["temperature"] = temperatureC;
//   doc["humidity"] = 55; // Default dummy humidity
//   doc["sensor_status"] = "ACTIVE";

//   String jsonString;
//   serializeJson(doc, jsonString);

//   // POST DATA
//   int httpResponseCode = http.POST(jsonString);

//   if (httpResponseCode > 0) {
//     Serial.printf("[HTTP] Response Code: %d\n", httpResponseCode);
//     String payload = http.getString();
//     Serial.println("[HTTP] Server Response: " + payload);
//   } else {
//     Serial.printf("[ERROR] HTTP Request failed, error: %s\n", http.errorToString(httpResponseCode).c_str());
//     Serial.println("[TIP] Check if Laptop IP is correct and Firewall is OFF for Port 5000.");
//   }

//   http.end();

//   // WAIT 5 SECONDS
//   delay(5000);
// }