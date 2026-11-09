import { router, useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { StyleSheet, useWindowDimensions, View } from 'react-native';

import { Button, Card, Icon, IconButton, Notice, Screen, Text } from '@/components/ui';
import { WidgetCard } from '@/components/widget-card';
import { MaxContentWidth, Spacing } from '@/constants/theme';
import { useSettings } from '@/context/settings';
import { useWidgets } from '@/context/widgets';

export default function Dashboard() {
  const { widgets, loaded } = useWidgets();
  const { api } = useSettings();
  const { width } = useWindowDimensions();
  const [refreshKey, setRefreshKey] = useState(0);

  // po navratu na dashboard (z detailu / nastaveni) obnovit hodnoty
  useFocusEffect(useCallback(() => setRefreshKey((k) => k + 1), []));

  const inner = Math.min(width, MaxContentWidth + Spacing.three * 2) - Spacing.three * 2;
  const cols = inner >= 900 ? 4 : inner >= 640 ? 3 : 2;
  const cardWidth = (inner - Spacing.three * (cols - 1)) / cols;

  const addWidget = () => router.push('/widget/edit');

  return (
    <Screen
      title="Přehled"
      right={<IconButton icon="add-circle-outline" label="Přidat widget" onPress={addWidget} color="accent" />}
      refreshing={false}
      onRefresh={() => setRefreshKey((k) => k + 1)}>
      {!api.url || !api.key ? (
        <Notice
          text="Nejdřív nastav adresu serveru a API klíč."
          action={<Button compact variant="secondary" label="Nastavení" onPress={() => router.navigate('/settings')} />}
        />
      ) : null}

      {loaded && widgets.length === 0 ? (
        <Card style={styles.empty}>
          <Icon name="grid-outline" size={40} color="textSecondary" />
          <Text variant="heading">Zatím tu nic není</Text>
          <Text color="textSecondary" style={{ textAlign: 'center', maxWidth: 360 }}>
            Přidej widget s hodnotou ze senzoru nebo fotovoltaiky. Můžeš zvolit poslední, průměrnou, minimální nebo
            maximální hodnotu.
          </Text>
          <Button label="Přidat widget" icon="add" onPress={addWidget} />
        </Card>
      ) : (
        <View style={styles.grid}>
          {widgets.map((w) => (
            <View key={w.id} style={{ width: cardWidth }}>
              <WidgetCard widget={w} refreshKey={refreshKey} />
            </View>
          ))}
          {widgets.length > 0 ? (
            <Card style={[styles.addCard, { width: cardWidth }]} onPress={addWidget} accessibilityLabel="Přidat widget">
              <Icon name="add" size={28} color="accent" />
              <Text variant="label" color="accent">
                Přidat widget
              </Text>
            </Card>
          ) : null}
        </View>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.three },
  empty: { alignItems: 'center', gap: Spacing.three, paddingVertical: Spacing.five },
  addCard: {
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.two,
    minHeight: 180,
    borderStyle: 'dashed',
  },
});
