#include <WiFi.h>
#include <HTTPClient.h>
#include <HardwareSerial.h>

// WiFi Credentials
const char* ssid = "vivo Y56 5G";
const char* password = "sourabh8";

// Google Script Web App URL
const char* scriptURL = "https://script.google.com/macros/s/AKfycbw0-QuOmfTsMgJbA4IoDoKom-CRfonBcKIWJEaNiRLUjb_SdMnWzW1ThyNCtWmKo85K6w/exec";

// RFID Reader on Serial2 (RX2 = GPIO16, TX2 = GPIO17)
HardwareSerial rfidSerial(2);

// RFID Card Database (Add your cards here)
struct CardData {
  String rfid_id;
  String name;
  String email;
  String phone;
  String address;
};

// Define your RFID cards and person details
CardData cardDatabase[] = {

  {"080073185E", "Sourabh Awale", "sourabh@example.com", "+91-9876543210", "Mumbai, India"},
  {"07009D8B5D", "Rahul Sharma", "rahul@example.com", "+91-9876543211", "Delhi, India"},
  {"0001270930", "Priya Singh", "priya@example.com", "+91-9876543212", "Banga lore, India"}
  // Add more cards as needed
};

const int totalCards = sizeof(cardDatabase) / sizeof(CardData);

void setup() {
  Serial.begin(115200);
  rfidSerial.begin(9600, SERIAL_8N1, 16, 17); // RX=16, TX=17
  
  
  Serial.println("Connecting to WiFi...");
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("\nWiFi Connected!");
  Serial.println("IP Address: " + WiFi.localIP().toString());
  Serial.println("\nReady to scan RFID cards...\n");
}

void loop() {
  if (rfidSerial.available()) {
    String rfidTag = "";
    
  
    while (rfidSerial.available() && rfidTag.length() < 12) {
      char c = rfidSerial.read();
      rfidTag += c;
      delay(5);
    }
    
    rfidTag = rfidTag.substring(0, 10);
    
    Serial.println("RFID Scanned: " + rfidTag);
    
  
    CardData* cardInfo = findCard(rfidTag);
    
    if (cardInfo != nullptr) {
      Serial.println("Card Found!");
      Serial.println("Name: " + cardInfo->name);
      sendToGoogleSheets(*cardInfo);
    } else {
      Serial.println("Unknown Card - Not in database");
    }
    
    Serial.println("------------------------\n");
    delay(2000); 
  }
}

CardData* findCard(String rfid) {
  for (int i = 0; i < totalCards; i++) {
    if (cardDatabase[i].rfid_id == rfid) {
      return &cardDatabase[i];
    }
  }
  return nullptr;
}

void sendToGoogleSheets(CardData card) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(scriptURL);
    http.addHeader("Content-Type", "application/json");
    http.setFollowRedirects(HTTPC_STRICT_FOLLOW_REDIRECTS);
    
    // Get current date and time
    String currentDate = getDate();
    String currentTime = getTime();
    
   
    String jsonData = "{";
    jsonData += "\"rfid_id\":\"" + card.rfid_id + "\",";
    jsonData += "\"name\":\"" + card.name + "\",";
    jsonData += "\"email\":\"" + card.email + "\",";
    jsonData += "\"phone\":\"" + card.phone + "\",";
    jsonData += "\"address\":\"" + card.address + "\",";
    jsonData += "\"date\":\"" + currentDate + "\",";
    jsonData += "\"time\":\"" + currentTime + "\"";
    jsonData += "}";
    
    Serial.println("Sending to Google Sheets...");
    int httpResponseCode = http.POST(jsonData);
    
    if (httpResponseCode > 0) {
      String response = http.getString();
      Serial.println("Response Code: " + String(httpResponseCode));
      Serial.println("Response: " + response);
      Serial.println("✓ Data logged successfully!");
    } else {
      Serial.println("Error: " + String(httpResponseCode));
    }
    
    http.end();
  } else {
    Serial.println("WiFi Disconnected!");
  }
}

String getDate() {
 
  time_t now = time(nullptr);
  struct tm* timeinfo = localtime(&now);
  
  char buffer[11];
  strftime(buffer, sizeof(buffer), "%d/%m/%Y", timeinfo);
  return String(buffer);
}

String getTime() {
  
  time_t now = time(nullptr);
  struct tm* timeinfo = localtime(&now);
  
  char buffer[9];
  strftime(buffer, sizeof(buffer), "%H:%M:%S", timeinfo);
  return String(buffer);
}
