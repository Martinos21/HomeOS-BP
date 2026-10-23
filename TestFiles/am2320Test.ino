#include <Arduino.h>
#ifndef ZIGBEE_MODE_ED
#error "V menu Tools -> Zigbee Mode musis vybrat 'Zigbee ED (End Device)'"
#endif


#define DEVICE_NAME "obyvak_teplota"
#define SENSOR_AM2320


#define I2C_SDA 2
#define I2C_SCL 3
#define DATA_PIN 4

#define SENSOR_ENDPOINT 10
#define REPORT_MS 30000

#include "Zigbee.h"


#if defined(SENSOR_AM2320)
#include <Wire.h>
#include "Adafruit_Sensor.h"
#include "Adafruit_AM2320.h"
#define SENSOR_NAME "AM2320"
#define SENSOR_HAS_HUMIDITY 1
#define SENSOR_TEMP_MIN -40
#define SENSOR_TEMP_MAX 80
Adafruit_AM2320 am2320;
bool sensorBegin() {
  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setClock(100000);
  delay(100);
  return am2320.begin();
}
bool sensorRead(float &temp, float &hum) {
  temp = am2320.readTemperature();
  hum = am2320.readHumidity();
  return !isnan(temp) && !isnan(hum);
}

ZigbeeTempSensor zbSensor = ZigbeeTempSensor(SENSOR_ENDPOINT);

void setup() {
  Serial.begin(115200);

  if (!sensorBegin()) {
    Serial.println("Senzor " SENSOR_NAME " se nepodarilo inicializovat!");
  } else {
    Serial.println("Senzor " SENSOR_NAME " inicializovan.");
  }

  zbSensor.setManufacturerAndModel("HomeOS", DEVICE_NAME);
  zbSensor.setMinMaxValue(SENSOR_TEMP_MIN, SENSOR_TEMP_MAX);
  zbSensor.setTolerance(0.5);
#if SENSOR_HAS_HUMIDITY
  zbSensor.addHumiditySensor(0, 100, 1);
#endif

  Zigbee.addEndpoint(&zbSensor);

  Serial.println("Startuji Zigbee...");
  if (!Zigbee.begin()) {
    Serial.println("Zigbee se nepodarilo spustit, restart...");
    ESP.restart();
  }
  while (!Zigbee.connected()) {
    Serial.print(".");
    delay(100);
  }
  Serial.println("\nPripojeno k Zigbee siti!");
}

void loop() {
  static unsigned long lastReport = 0;
  if (millis() - lastReport > REPORT_MS) {
    lastReport = millis();
    float temp = NAN, hum = NAN;
    if (!sensorRead(temp, hum)) {
      Serial.println("Cteni " SENSOR_NAME " selhalo");
      return;
    }
    zbSensor.setTemperature(temp);
#if SENSOR_HAS_HUMIDITY
    zbSensor.setHumidity(hum);
#endif
    zbSensor.report();
    Serial.printf("Odeslano: %.2f C", temp);
#if SENSOR_HAS_HUMIDITY
    Serial.printf(", %.1f %%", hum);
#endif
    Serial.println();
  }
  delay(100);
}
