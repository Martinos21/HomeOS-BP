import { StyleSheet, View } from 'react-native';

import { Button, Card, Icon, Screen, Text, type IconName } from '@/components/ui';
import { Spacing } from '@/constants/theme';

/** Automatizace: zatim jen nahled, logika se bude doimplementovavat v backendu. */
const PLANNED: { icon: IconName; title: string; text: string }[] = [
  { icon: 'thermometer-outline', title: 'Když teplota klesne pod…', text: 'Spuštění akce podle hodnoty senzoru.' },
  { icon: 'walk-outline', title: 'Když se detekuje pohyb…', text: 'Reakce na pohybový senzor.' },
  { icon: 'time-outline', title: 'Každý den v…', text: 'Akce podle času.' },
  { icon: 'battery-charging-outline', title: 'Když je baterie nabitá nad…', text: 'Využití přebytků z fotovoltaiky.' },
];

export default function Automations() {
  return (
    <Screen title="Automatizace" right={<Button compact label="Nová" icon="add" disabled />}>
      <Card style={styles.hero}>
        <Icon name="construct-outline" size={36} color="accent" />
        <Text variant="heading">Připravujeme</Text>
        <Text color="textSecondary" style={{ textAlign: 'center', maxWidth: 420 }}>
          Tady bude možné nastavit pravidla typu „když … pak …“. Stránka je připravená, logika se teprve doplní do
          backendu.
        </Text>
      </Card>

      <Text variant="label" color="textSecondary" style={{ textTransform: 'uppercase' }}>
        Plánované spouštěče
      </Text>
      <View style={styles.list}>
        {PLANNED.map((p) => (
          <Card key={p.title} style={[styles.item, { opacity: 0.7 }]}>
            <Icon name={p.icon} size={22} color="textSecondary" />
            <View style={{ flex: 1 }}>
              <Text variant="heading">{p.title}</Text>
              <Text variant="caption" color="textSecondary">
                {p.text}
              </Text>
            </View>
          </Card>
        ))}
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  hero: { alignItems: 'center', gap: Spacing.two, paddingVertical: Spacing.four },
  list: { gap: Spacing.two },
  item: { flexDirection: 'row', alignItems: 'center', gap: Spacing.three },
});
