#include <Wire.h>
#include "Adafruit_Sensor.h"
#include "Adafruit_AM2320.h"

// Uprav podle sveho zapojeni
#define I2C_SDA 2
#define I2C_SCL 3

Adafruit_AM2320 am2320 = Adafruit_AM2320();

void setup() {
  Serial.begin(9600);
  while (!Serial) {
    delay(10);
  }

  Serial.println("AM2320 test teploty a vlhkosti");

  // DULEZITE: na ESP32-C5 neni pevny vychozi I2C pin,
  // musi se nastavit rucne pred am2320.begin()
  Wire.begin(I2C_SDA, I2C_SCL);

  am2320.begin();
}

void loop() {
  float teplota = am2320.readTemperature();
  float vlhkost = am2320.readHumidity();

  Serial.print("Teplota: ");
  Serial.print(teplota);
  Serial.println(" C");

  Serial.print("Vlhkost: ");
  Serial.print(vlhkost);
  Serial.println(" %RH");

  delay(2000);
}