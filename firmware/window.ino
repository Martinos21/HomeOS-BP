
#include <Arduino.h>
#include "Zigbee.h"

#define pinA 2

#define CO2_ENDPOINT 10

ZigbeeContactSwitch zbWindowSensor = ZigbeeContactSwitch(CO2_ENDPOINT);

void setup() {
  Serial.begin(115200);
  pinMode(pinA, INPUT);

  // Volitelne: nazev vyrobce a modelu
  zbWindowSensor.setManufacturerAndModel("DIY", "WindowSensor");

  // Pridani endpointu do Zigbee
  Zigbee.addEndpoint(&zbWindowSensor);

  Serial.println("Startuji Zigbee...");
  if (!Zigbee.begin()) {
    Serial.println("Zigbee se nepodarilo spustit, restart...");
    ESP.restart();
  }

  Serial.println("Pripojuji se k siti...");
  while (!Zigbee.connected()) {
    Serial.print(".");
    delay(100);
  }
  Serial.println("\nPripojeno k Zigbee siti!");
}

void loop() {
  static unsigned long lastReport = 0;
  if (millis() - lastReport > 10000) {
    int stav = digitalRead(pinA);
    Serial.println("Stav je:");
    Serial.println(stav);
    if (stav == 1) {
      zbWindowSensor.setOpen();
    } else {
      zbWindowSensor.setClosed();
    }
    lastReport = millis();
  }
  delay(100);
}