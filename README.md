# 🏠 HomeOS-BP

A smart home system running on a Raspberry Pi. HomeOS collects data from the whole household
in one place, stores it, and will later present it in a clear web interface.

## ✨ Features

- 🌡️ **Room temperature and humidity**: small ESP sensors send readings wirelessly over Zigbee
- ☀️ **Solar power**: every few minutes it fetches production, consumption, grid export and battery status
- 💾 **Data history**: all measurements are stored in a single database
- 🔗 **Easy sensor setup**: just pair a new ESP and the system names it and starts recording automatically
- 🌐 **Web API and frontend** *(coming soon)*: access your data and controls from anywhere

## 🧩 Components

| | part | what it does |
|---|---|---|
| 📡 | `zigbee/` | receives sensor data and handles pairing of new devices ([more info](zigbee/README.md)) |
| 🔌 | `zigbee/esp/` | firmware for the ESP sensors, one sketch for all, only the name and sensor type change |
| ☀️ | `solarAPI/` | fetches data from the solar power system |
| 🖥️ | `backend/` | public API for the frontend *(in development)* |
| 🧪 | `TestFiles/` | older experiments and prototypes |
| 📄 | `docs/` | bachelor thesis documentation |

## 🚀 How it works

```
🌡️ ESP sensors ──Zigbee──► 🍓 Raspberry Pi ──► 💾 database ──► 🖥️ backend ──► 📱 frontend
☀️ solar power ──internet──────────┘
```

## 📜 License

MIT, see [LICENSE](LICENSE).
