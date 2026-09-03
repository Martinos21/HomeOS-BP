#include <Arduino.h>
#ifndef ZIGBEE_MODE_ED
#error "V menu Tools -> Zigbee Mode musis vybrat 'Zigbee ED (End Device)'"
#endif

#include "Zigbee.h"

#define TEMP_SENSOR_ENDPOINT 10

ZigbeeTempSensor zbTempSensor = ZigbeeTempSensor(TEMP_SENSOR_ENDPOINT);

void setup() {
  Serial.begin(115200);

  // Volitelne: nazev vyrobce a modelu
  zbTempSensor.setManufacturerAndModel("DIY", "TempSensor");

  // Rozsah teplot (min, max)
  zbTempSensor.setMinMaxValue(-10, 50);

  // Pridani endpointu do Zigbee
  Zigbee.addEndpoint(&zbTempSensor);

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

  // Nastav teplotu na 10 a odesli
  zbTempSensor.setTemperature(10.0);
  zbTempSensor.reportTemperature();
  Serial.println("Odeslano: temp:22");
}

void loop() {
  static unsigned long lastReport = 0;
  if (millis() - lastReport > 10000) {
    zbTempSensor.setTemperature(10.0);
    bool ok = zbTempSensor.reportTemperature();
    Serial.printf("Report odeslan: %s\n", ok ? "OK" : "SELHAL");
    lastReport = millis();
  }
  delay(100);
}