import Constants from 'expo-constants';
import { useState } from 'react';
import { ActivityIndicator, Platform, View } from 'react-native';

import { Button, Card, Field, Icon, InfoRow, Notice, Screen, SectionTitle, Segmented, Text } from '@/components/ui';
import { Spacing } from '@/constants/theme';
import { useSettings, type ThemeMode } from '@/context/settings';
import { useAsync } from '@/hooks/use-async';
import { api } from '@/lib/api';
import { formatDuration } from '@/lib/format';

const THEMES: { value: ThemeMode; label: string }[] = [
  { value: 'system', label: 'Podle systému' },
  { value: 'light', label: 'Světlý' },
  { value: 'dark', label: 'Tmavý' },
];

export default function Settings() {
  const s = useSettings();
  const [url, setUrl] = useState(s.apiUrl);
  const [key, setKey] = useState(s.apiKey);
  const [testing, setTesting] = useState(false);
  const [test, setTest] = useState<{ ok: boolean; text: string } | null>(null);

  const system = useAsync(() => api.system(s.api), [s.api.url, s.api.key]);

  const dirty = url.trim() !== s.apiUrl || key.trim() !== s.apiKey;

  const saveAndTest = async () => {
    const cfg = { url: url.trim(), key: key.trim() };
    s.update({ apiUrl: cfg.url, apiKey: cfg.key });
    setTesting(true);
    setTest(null);
    try {
      await api.devices(cfg); // overi i API klic (health ho nechce)
      setTest({ ok: true, text: 'Připojeno.' });
    } catch (e) {
      setTest({ ok: false, text: e instanceof Error ? e.message : String(e) });
    } finally {
      setTesting(false);
    }
  };

  const sys = system.data;
  const rn = Platform.constants?.reactNativeVersion;

  return (
    <Screen title="Nastavení">
      <SectionTitle>Vzhled</SectionTitle>
      <Card style={{ gap: Spacing.two }}>
        <Text>Režim</Text>
        <Segmented value={s.themeMode} options={THEMES} onChange={(v) => s.update({ themeMode: v })} />
      </Card>

      <SectionTitle>Připojení k HomeOS</SectionTitle>
      <Card style={{ gap: Spacing.three }}>
        <Field
          label="Adresa serveru"
          placeholder="http://192.168.1.50:8080"
          value={url}
          onChangeText={setUrl}
          keyboardType="url"
          hint="Raspberry Pi s backendem (uv run python -m backend.app)."
        />
        <Field
          label="API klíč"
          placeholder="HOMEOS_API_KEY z .env"
          value={key}
          onChangeText={setKey}
          secureTextEntry
        />
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: Spacing.two, flexWrap: 'wrap' }}>
          <Button label={dirty ? 'Uložit a otestovat' : 'Otestovat'} icon="link-outline" loading={testing} onPress={saveAndTest} />
          {test ? (
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: Spacing.one, flexShrink: 1 }}>
              <Icon name={test.ok ? 'checkmark-circle' : 'close-circle'} color={test.ok ? 'success' : 'danger'} />
              <Text color={test.ok ? 'success' : 'danger'} style={{ flexShrink: 1 }}>
                {test.text}
              </Text>
            </View>
          ) : null}
        </View>
      </Card>

      <SectionTitle>Systém (Raspberry Pi)</SectionTitle>
      <Card style={{ paddingVertical: Spacing.one }}>
        {system.error ? (
          <View style={{ paddingVertical: Spacing.two }}>
            <Notice tone="error" text={system.error} action={<Button compact variant="secondary" label="Znovu" onPress={system.reload} />} />
          </View>
        ) : !sys ? (
          <View style={{ padding: Spacing.three }}>
            <ActivityIndicator />
          </View>
        ) : (
          <>
            <InfoRow icon="server-outline" label="Hostname" value={sys.hostname} />
            <InfoRow icon="logo-tux" label="Linux" value={sys.os} />
            <InfoRow icon="hardware-chip-outline" label="Kernel" value={`${sys.kernel} (${sys.arch})`} />
            <InfoRow icon="logo-python" label="Python" value={`${sys.python_impl} ${sys.python}`} />
            <InfoRow icon="time-outline" label="Systém běží" value={formatDuration(sys.uptime_s)} />
            <InfoRow icon="pulse-outline" label="Backend běží" value={formatDuration(sys.api_uptime_s)} />
            <InfoRow
              icon="radio-outline"
              label="Zigbee"
              value={
                <Text color={sys.zigbee_online ? 'success' : 'danger'}>{sys.zigbee_online ? 'Online' : 'Offline'}</Text>
              }
            />
            <InfoRow icon="hardware-chip-outline" label="Spárovaná ESP" value={String(sys.device_count)} />
            <InfoRow icon="folder-outline" label="Databáze" value={sys.db_path} last />
          </>
        )}
      </Card>

      <SectionTitle>Aplikace</SectionTitle>
      <Card style={{ paddingVertical: Spacing.one }}>
        <InfoRow icon="apps-outline" label="Verze aplikace" value={Constants.expoConfig?.version ?? '–'} />
        <InfoRow icon="cube-outline" label="Expo SDK" value={Constants.expoConfig?.sdkVersion ?? '–'} />
        <InfoRow
          icon="phone-portrait-outline"
          label="Platforma"
          value={`${Platform.OS}${Platform.OS !== 'web' ? ` ${Platform.Version}` : ''}`}
        />
        <InfoRow
          icon="logo-react"
          label="React Native"
          value={rn ? `${rn.major}.${rn.minor}.${rn.patch}` : '–'}
          last
        />
      </Card>
    </Screen>
  );
}
