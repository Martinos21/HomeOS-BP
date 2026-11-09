import { router } from 'expo-router';
import { ActivityIndicator, StyleSheet, View } from 'react-native';

import { LineChart } from '@/components/line-chart';
import { Card, Icon, Text, type IconName } from '@/components/ui';
import { Spacing } from '@/constants/theme';
import { useSettings } from '@/context/settings';
import { useAsync } from '@/hooks/use-async';
import { api } from '@/lib/api';
import { describeSource, formatValue, RANGE_LABEL, STAT_LABEL, timeAgo } from '@/lib/format';
import type { Widget } from '@/lib/types';

/** Jeden widget na dashboardu: velka hodnota (posledni/prumer/min/max) + mini graf. */
export function WidgetCard({ widget, refreshKey }: { widget: Widget; refreshKey: number }) {
  const { api: cfg } = useSettings();
  const d = describeSource(widget.source);
  const key = JSON.stringify([widget.source, widget.range, cfg, refreshKey]);
  const stats = useAsync(() => api.stats(cfg, widget.source, widget.range), [key], 30000);
  const spark = useAsync(() => api.history(cfg, widget.source, widget.range, 40), [key], 60000);

  const value = stats.data ? stats.data[widget.stat] : null;
  const stale = stats.data?.last_at && Date.now() - new Date(stats.data.last_at).getTime() > 30 * 60e3;

  return (
    <Card
      style={styles.card}
      onPress={() => router.push({ pathname: '/widget/[id]', params: { id: widget.id } })}
      accessibilityLabel={`${widget.title || d.label}, ${STAT_LABEL[widget.stat]} ${formatValue(value, d.digits)} ${d.unit}`}>
      <View style={styles.top}>
        <Icon name={d.icon as IconName} size={18} color="accent" />
        <Text variant="label" color="textSecondary" numberOfLines={1} style={{ flex: 1 }}>
          {d.group}
        </Text>
        {stats.loading && !stats.data ? <ActivityIndicator size="small" /> : null}
      </View>
      <Text variant="heading" numberOfLines={1}>
        {widget.title || d.label}
      </Text>

      {stats.error ? (
        <Text variant="caption" color="danger" numberOfLines={3}>
          {stats.error}
        </Text>
      ) : (
        <View style={styles.valueRow}>
          <Text variant="value">{formatValue(value, d.digits)}</Text>
          {d.unit ? (
            <Text variant="heading" color="textSecondary">
              {d.unit}
            </Text>
          ) : null}
        </View>
      )}

      <View style={{ height: 40 }}>
        {spark.data && spark.data.length > 1 ? <LineChart points={spark.data} height={40} sparkline /> : null}
      </View>

      <View style={styles.bottom}>
        <Text variant="caption" color="textSecondary" numberOfLines={1} style={{ flex: 1 }}>
          {STAT_LABEL[widget.stat]} · {widget.stat === 'last' ? timeAgo(stats.data?.last_at) : RANGE_LABEL[widget.range]}
        </Text>
        {stale ? <Icon name="time-outline" size={14} color="warning" /> : null}
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  card: { gap: Spacing.one, flex: 1 },
  top: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two },
  valueRow: { flexDirection: 'row', alignItems: 'baseline', gap: Spacing.one, marginTop: Spacing.one },
  bottom: { flexDirection: 'row', alignItems: 'center', gap: Spacing.one },
});
