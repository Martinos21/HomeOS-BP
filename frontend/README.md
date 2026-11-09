# HomeOS frontend (Expo / React Native)

Jedna aplikace pro **web, Android i iOS** (Expo SDK 58, Expo Router).

## Stránky
- **Přehled** (`src/app/(tabs)/index.tsx`): widgety, které si uživatel přidá. Každý ukazuje
  poslední / průměrnou / minimální / maximální hodnotu za zvolené období + mini graf.
  Klik na widget → **detail** (`src/app/widget/[id].tsx`) s grafem průběhu všech hodnot z DB
  (1 h / 24 h / 7 dní / 30 dní / vše), souhrnem a úpravou / smazáním widgetu.
- **Automatizace** (`src/app/(tabs)/automations.tsx`): zatím připravená stránka.
- **Nastavení** (`src/app/(tabs)/settings.tsx`): světlý / tmavý / podle systému, adresa serveru
  a API klíč, info o Pi (Linux, kernel, Python, uptime, Zigbee, DB) a o aplikaci.

## Spuštění
```
npm install
npx expo start          # w = web, a = Android, i = iOS (Expo Go)
npx expo export -p web  # statický web do dist/ (SPA)
```
Výchozí adresa je `http://localhost:8080` a ze stejného zařízení backend klíč nechce. Z mobilu zadej v Nastavení IP adresu (např. `http://192.168.1.50:8080`) a `HOMEOS_API_KEY` z `backend/.env`.

## Struktura
- `src/lib/api.ts` volání backendu, `src/lib/format.ts` popisky a jednotky hodnot
- `src/context/settings.tsx` téma + připojení, `src/context/widgets.tsx` widgety
  (ukládají se lokálně v zařízení přes AsyncStorage / localStorage)
- `src/components/line-chart.tsx` graf (react-native-svg), `src/components/ui.tsx` UI prvky

## Použité endpointy (backend/app.py)
`/api/devices`, `/api/solar`, `/api/{devices|solar}/<x>/stats`, `/api/{devices|solar}/<x>/history`,
`/api/system`
