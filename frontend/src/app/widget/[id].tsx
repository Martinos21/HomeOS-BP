import { router, Stack, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';

import { LineChart } from '@/components/line-chart';
import { Button, Card, Notice, Screen, Segmented, Text } from '@/components/ui';
import { Spacing } from '@/constants/theme';
import { useColors, useSettings } from '@/context/settings';
import { useWidgets } from '@/context/widgets';
import { useAsync } from '@/hooks/use-async';
import { api } from '@/lib/api';
import { confirm } from '@/lib/confirm';
import { describeSource, formatDateTime, formatValue, RANGE_LABEL, STAT_LABEL } from '@/lib/format';
import type { Range, Stat } from '@/lib/types';

const RANGES = (Object.keys(RANGE_LABEL) as Range[]).map((r) => ({ value: r, label: RANGE_LABEL[r] }));
const STATS: Stat[] = ['last', 'avg', 'min', 'max'];

/** Detail widgetu: prubeh vsech hodnot z databaze + souhrn za zvolene obdobi. */
export default function WidgetDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { widgets, remove, move, update } = useWidgets();
  const { api: cfg } = useSettings();
  const c = useColors();
  const widget = widgets.find((w) => w.id === id);
  const [range, setRangeState] = useState<Range>(widget?.range ?? '24h');
  // zvolene obdobi se ulozi do widgetu -> prumer/min/max na prehledu se pocita za nej
  const setRange = (r: Range) => {
    setRangeState(r);
    if (widget) update(widget.id, { range: r });
  };

  const key = JSON.stringify([widget?.source, range, cfg]);
  const history = useAsync(
    () => (widget ? api.history(cfg, widget.source, range, 300) : Promise.resolve([])),
    [key],
    60000,
  );
  const stats = useAsync(
    () => (widget ? api.stats(cfg, widget.source, range) : Promise.resolve(null)),
    [key],
    60000,
  );

  if (!widget) {
    return (
      <Screen tabs={false}>
        <Notice text="Widget neexistuje (možná byl smazán)." />
        <Button label="Zpět na přehled" onPress={() => router.navigate('/')} />
      </Screen>
    );
  }

  const d = describeSource(widget.source);
  const title = widget.title || d.label;
  const index = widgets.findIndex((w) => w.id === widget.id);

  const onDelete = async () => {
    if (await confirm('Smazat widget?', `„${title}“ zmizí z přehledu. Data v databázi zůstanou.`)) {
      remove(widget.id);
      router.back();
    }
  };

  return (
    <>
      <Stack.Screen options={{ title }} />
      <Screen tabs={false} refreshing={false} onRefresh={() => (history.reload(), stats.reload())}>
        <View style={{ gap: Spacing.one }}>
          <Text variant="label" color="textSecondary">
            {d.group}
          </Text>
          <Text variant="title">{title}</Text>
        </View>

        <Segmented value={range} options={RANGES} onChange={setRange} />

        <View style={styles.stats}>
          {STATS.map((s) => (
            <Card
              key={s}
              style={[styles.stat, s === widget.stat && { borderColor: c.accent }]}>
              <Text variant="caption" color="textSecondary">
                {STAT_LABEL[s]}
              </Text>
              <Text variant="heading">
                {formatValue(stats.data?.[s], d.digits)} {stats.data?.[s] != null ? d.unit : ''}
              </Text>
            </Card>
          ))}
        </View>

        <Card style={{ gap: Spacing.two }}>
          {history.error ? (
            <Notice tone="error" text={history.error} action={<Button compact variant="secondary" label="Znovu" onPress={history.reload} />} />
          ) : history.loading && !history.data ? (
            <View style={styles.placeholder}>
              <ActivityIndicator />
            </View>
          ) : history.data && history.data.length > 0 ? (
            <LineChart points={history.data} digits={d.digits} unit={d.unit} />
          ) : (
            <View style={styles.placeholder}>
              <Text color="textSecondary">Za zvolené období nejsou žádná data.</Text>
            </View>
          )}
          <Text variant="caption" color="textSecondary">
            {stats.data
              ? `${stats.data.count.toLocaleString('cs-CZ')} měření · poslední ${formatDateTime(stats.data.last_at)}` +
                (history.data && history.data.length && history.data.some((p) => p.min !== p.max)
                  ? ' · světlý pruh = rozsah min–max v úseku'
                  : '')
              : ' '}
          </Text>
        </Card>

        <View style={styles.actions}>
          <Button
            label="Upravit"
            icon="create-outline"
            variant="secondary"
            onPress={() => router.push({ pathname: '/widget/edit', params: { id: widget.id } })}
          />
          <Button label="Dřív" icon="arrow-back" variant="ghost" disabled={index <= 0} onPress={() => move(widget.id, -1)} />
          <Button
            label="Později"
            icon="arrow-forward"
            variant="ghost"
            disabled={index >= widgets.length - 1}
            onPress={() => move(widget.id, 1)}
          />
          <View style={{ flex: 1 }} />
          <Button label="Smazat" icon="trash-outline" variant="danger" onPress={onDelete} />
        </View>
      </Screen>
    </>
  );
}

const styles = StyleSheet.create({
  stats: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two },
  stat: { flexGrow: 1, flexBasis: 140, gap: Spacing.half, paddingVertical: Spacing.two + 4 },
  placeholder: { height: 260, alignItems: 'center', justifyContent: 'center' },
  actions: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two, alignItems: 'center' },
});
