import { router, Stack, useLocalSearchParams } from 'expo-router';
import { useMemo, useState } from 'react';
import { ActivityIndicator, View } from 'react-native';

import { Button, Card, Chips, Field, Notice, Screen, SectionTitle, Segmented, Text, type IconName } from '@/components/ui';
import { Spacing } from '@/constants/theme';
import { useSettings } from '@/context/settings';
import { useWidgets } from '@/context/widgets';
import { useAsync } from '@/hooks/use-async';
import { api } from '@/lib/api';
import {
  columnLabel,
  describeSource,
  formatValue,
  prettyName,
  RANGE_LABEL,
  solarColumnLabel,
  STAT_LABEL,
} from '@/lib/format';
import type { Range, Source, Stat } from '@/lib/types';

const STATS = (Object.keys(STAT_LABEL) as Stat[]).map((s) => ({ value: s, label: STAT_LABEL[s] }));
const RANGES = (Object.keys(RANGE_LABEL) as Range[]).map((r) => ({ value: r, label: RANGE_LABEL[r] }));

/** Pridani / uprava widgetu: zdroj (ESP nebo solar) -> hodnota -> statistika -> obdobi. */
export default function EditWidget() {
  const { id } = useLocalSearchParams<{ id?: string }>();
  const { widgets, add, update } = useWidgets();
  const { api: cfg } = useSettings();
  const existing = widgets.find((w) => w.id === id);

  // zdroj jako "device:<name>" / "solar:<metric>", hodnota zvlast
  const [sourceKey, setSourceKey] = useState<string | null>(
    existing ? (existing.source.kind === 'device' ? `device:${existing.source.name}` : `solar:${existing.source.metric}`) : null,
  );
  const [column, setColumn] = useState<string | null>(existing?.source.column ?? null);
  const [stat, setStat] = useState<Stat>(existing?.stat ?? 'last');
  const [range, setRange] = useState<Range>(existing?.range ?? '24h');
  const [title, setTitle] = useState(existing?.title ?? '');

  const sources = useAsync(async () => {
    const [devices, solar] = await Promise.all([api.devices(cfg), api.solar(cfg).catch(() => [])]);
    return { devices, solar };
  }, [cfg.url, cfg.key]);

  const sourceOptions = useMemo(() => {
    const opts: { value: string; label: string; icon?: IconName; columns: { value: string; label: string }[] }[] = [];
    for (const d of sources.data?.devices ?? []) {
      opts.push({
        value: `device:${d.name}`,
        label: prettyName(d.name),
        icon: 'hardware-chip-outline',
        columns: d.columns.map((c) => ({ value: c, label: columnLabel(c) })),
      });
    }
    for (const m of sources.data?.solar ?? []) {
      const desc = describeSource({ kind: 'solar', metric: m.metric, column: 'total' });
      opts.push({
        value: `solar:${m.metric}`,
        label: desc.label,
        icon: 'sunny-outline',
        columns: m.columns.map((c) => ({ value: c, label: solarColumnLabel(c) })),
      });
    }
    return opts;
  }, [sources.data]);

  const selected = sourceOptions.find((o) => o.value === sourceKey);

  const source: Source | null = useMemo(() => {
    if (!sourceKey || !column) return null;
    const [kind, ...rest] = sourceKey.split(':');
    const name = rest.join(':');
    return kind === 'device'
      ? { kind: 'device', name, column }
      : { kind: 'solar', metric: name, column: column as 'total' | 'delta' };
  }, [sourceKey, column]);

  const preview = useAsync(
    () => (source ? api.stats(cfg, source, range) : Promise.resolve(null)),
    [JSON.stringify([source, range, cfg])],
  );

  const chooseSource = (v: string) => {
    setSourceKey(v);
    const opt = sourceOptions.find((o) => o.value === v);
    // jedna hodnota -> rovnou vybrat, jinak zachovat pokud existuje
    if (opt && !opt.columns.some((c) => c.value === column)) setColumn(opt.columns[0]?.value ?? null);
  };

  const save = () => {
    if (!source) return;
    const data = { source, stat, range, title: title.trim() || undefined };
    if (existing) update(existing.id, data);
    else add(data);
    router.back();
  };

  const d = source ? describeSource(source) : null;

  return (
    <>
      <Stack.Screen options={{ title: existing ? 'Upravit widget' : 'Nový widget' }} />
      <Screen tabs={false}>
        <SectionTitle>1. Zdroj dat</SectionTitle>
        {sources.error ? (
          <Notice tone="error" text={sources.error} action={<Button compact variant="secondary" label="Znovu" onPress={sources.reload} />} />
        ) : sources.loading && !sources.data ? (
          <ActivityIndicator />
        ) : sourceOptions.length === 0 ? (
          <Notice text="V databázi zatím není žádné zařízení. Spáruj ESP nebo spusť solarAPI." />
        ) : (
          <Chips value={sourceKey} options={sourceOptions} onChange={chooseSource} />
        )}

        {selected ? (
          <>
            <SectionTitle>2. Hodnota</SectionTitle>
            <Chips value={column} options={selected.columns} onChange={setColumn} />
          </>
        ) : null}

        <SectionTitle>3. Co zobrazit</SectionTitle>
        <Segmented value={stat} options={STATS} onChange={setStat} />

        <SectionTitle>{stat === 'last' ? '4. Období mini grafu' : '4. Za jaké období'}</SectionTitle>
        <Segmented value={range} options={RANGES} onChange={setRange} />

        <SectionTitle>5. Název (nepovinné)</SectionTitle>
        <Field label="Vlastní název" placeholder={d?.label ?? 'např. Obývák'} value={title} onChangeText={setTitle} autoCapitalize="sentences" />

        {source && d ? (
          <Card style={{ gap: Spacing.one }}>
            <Text variant="caption" color="textSecondary">
              Náhled · {STAT_LABEL[stat]} {stat === 'last' ? '' : `za ${RANGE_LABEL[range]}`}
            </Text>
            <Text variant="heading">{title.trim() || d.label}</Text>
            {preview.error ? (
              <Text color="danger">{preview.error}</Text>
            ) : (
              <Text variant="value">
                {formatValue(preview.data?.[stat], d.digits)} {d.unit}
              </Text>
            )}
          </Card>
        ) : null}

        <View style={{ flexDirection: 'row', gap: Spacing.two, justifyContent: 'flex-end' }}>
          <Button label="Zrušit" variant="ghost" onPress={() => router.back()} />
          <Button label={existing ? 'Uložit' : 'Přidat na přehled'} icon="checkmark" disabled={!source} onPress={save} />
        </View>
      </Screen>
    </>
  );
}
