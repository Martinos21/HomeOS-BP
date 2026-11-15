#include <Arduino.h>
#ifndef ZIGBEE_MODE_ED
#error "V menu Tools -> Zigbee Mode musis vybrat 'Zigbee ED (End Device)'"
#endif

#include "Adafruit_Sensor.h"
#include "Adafruit_AM2320.h"
#include "Zigbee.h"

#define pinA 2 //21
#define pinD 3 //22

#define TEMP_SENSOR_ENDPOINT 10

Adafruit_AM2320 am2320 = Adafruit_AM2320();
ZigbeeTempSensor zbTempSensor = ZigbeeTempSensor(TEMP_SENSOR_ENDPOINT);

void setup() {
  Serial.begin(115200);

  Wire.begin(I2C_SDA,I2C_SCL);
  Wire.setClock(100000);
  delay(100);
  am2320.begin();
  delay(100);

  if (!am2320.begin()) {
    Serial.println("Nepodarilo se inicializovat AM2320!");
  } else {
    Serial.println("Senzor AM2320 inicializovan.");
  }

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
  zbTempSensor.setTemperature(0);
  zbTempSensor.reportTemperature();
  Serial.println("Odeslano: temp:22");
}

void loop() {
  static unsigned long lastReport = 0;
  if (millis() - lastReport > 10000) {
    float teplota = am2320.readTemperature();
    Serial.println("teplota je:");
    Serial.println(teplota);
    zbTempSensor.setTemperature(teplota);
    bool ok = zbTempSensor.reportTemperature();
    Serial.printf("Report odeslan: %s\n", ok ? "OK" : "SELHAL");
    lastReport = millis();
  }
  delay(100);
}