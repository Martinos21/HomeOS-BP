/*// MQ-135 senzor plynů

// připojení potřebné knihovny
#include "MQ135.h"
// nastavení propojovacích pinů
#define pinA A0
#define pinD 2
// inicializace senzoru z knihovny
MQ135 senzorMQ = MQ135(pinA);

void setup() {
  // inicializace komunikace po sériové lince
  // rychlostí 9600 baud
  Serial.begin(9600);
  // nastavení přerušení na pin 2 (int0)
  // při nástupné hraně (log0->log1) se vykoná program prerus
  attachInterrupt(digitalPinToInterrupt(pinD), prerus, RISING);
}
void loop() {
  // načtení koncentrace plynů v ppm do proměnné
  float ppm = senzorMQ.getPPM();
  // načtení času od spuštění Arduina v sekundách
  long cas = millis()/1000;
  // vytištění naměřené koncentrace
  Serial.print("Koncentrace plynů: ");
  Serial.print(ppm);
  Serial.print(" ppm | cas od spusteni Arduina: ");
  Serial.print(cas/60); // výpočet minut - dělení 60
  Serial.print("m");
  Serial.print(cas%60); // výpočet vteřin - zbytek po dělení 60
  Serial.println("s.");

  // pauza před dalším měřením
  delay(3000);
}
void prerus() {
  // vypiš varovnou hlášku, pokud je aktivován digitální vstup
  Serial.println("Detekovano prekroceni hranice!");
}*/

#include <Arduino.h>
#include "MQ135.h"
#include "Zigbee.h"

#define pinA 3
#define pinD 2
#define CO2_ENDPOINT 10

MQ135 senzorMQ = MQ135(pinA, 630.0);
ZigbeeCarbonDioxideSensor zbCO2Sensor = ZigbeeCarbonDioxideSensor(CO2_ENDPOINT);

void setup() {
  Serial.begin(115200);
  analogReadResolution(10);   // knihovna MQ135 pocita s rozsahem 0-1023

  // Volitelne: nazev vyrobce a modelu
  zbCO2Sensor.setManufacturerAndModel("DIY", "CO2Sensor");

  // Rozsah CO2 v ppm (min, max)
  zbCO2Sensor.setMinMaxValue(0, 5000);

  // Pridani endpointu do Zigbee
  Zigbee.addEndpoint(&zbCO2Sensor);

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
    float co2 = senzorMQ.getPPM();
    Serial.println("CO2 je:");
    Serial.println(co2);
    zbCO2Sensor.setCarbonDioxide(co2);
    zbCO2Sensor.report();
    lastReport = millis();
  }
  delay(100);
}