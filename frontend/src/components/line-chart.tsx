import { useMemo, useState } from 'react';
import { StyleSheet, View, type GestureResponderEvent, type LayoutChangeEvent } from 'react-native';
import Svg, { Circle, Line, Path, Text as SvgText } from 'react-native-svg';

import { Text } from '@/components/ui';
import { Fonts, Radius, Spacing } from '@/constants/theme';
import { useColors } from '@/context/settings';
import { formatAxisTime, formatDateTime, formatValue } from '@/lib/format';
import type { HistoryPoint } from '@/lib/types';

const PAD = { top: 12, right: 12, bottom: 26, left: 48 };

function niceTicks(min: number, max: number, count = 4) {
  if (min === max) {
    min -= 1;
    max += 1;
  }
  const raw = (max - min) / count;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? raw;
  const lo = Math.floor(min / step) * step;
  const hi = Math.ceil(max / step) * step;
  const ticks: number[] = [];
  for (let v = lo; v <= hi + step / 2; v += step) ticks.push(Number(v.toFixed(10)));
  return { lo, hi, ticks };
}

/**
 * Graf prubehu: cara = prumer v useku, pruh = min..max v useku
 * (backend vraci data zhustena na ~300 bodu). Dotykem / mysi se ukaze hodnota.
 */
export function LineChart({
  points,
  height = 260,
  digits = 1,
  unit = '',
  sparkline = false,
}: {
  points: HistoryPoint[];
  height?: number;
  digits?: number;
  unit?: string;
  sparkline?: boolean;
}) {
  const c = useColors();
  const [width, setWidth] = useState(0);
  const [active, setActive] = useState<number | null>(null);
  const pad = sparkline ? { top: 3, right: 2, bottom: 3, left: 2 } : PAD;

  const geo = useMemo(() => {
    if (points.length === 0 || width === 0) return null;
    const ts = points.map((p) => new Date(p.at).getTime());
    const t0 = ts[0];
    const t1 = ts[ts.length - 1] === t0 ? t0 + 1 : ts[ts.length - 1];
    let lo = Math.min(...points.map((p) => p.min));
    let hi = Math.max(...points.map((p) => p.max));
    const { ticks, lo: tlo, hi: thi } = niceTicks(lo, hi);
    if (!sparkline) {
      lo = tlo;
      hi = thi;
    } else if (lo === hi) {
      lo -= 1;
      hi += 1;
    }
    const w = width - pad.left - pad.right;
    const h = height - pad.top - pad.bottom;
    const x = (t: number) => pad.left + ((t - t0) / (t1 - t0)) * w;
    const y = (v: number) => pad.top + (1 - (v - lo) / (hi - lo)) * h;

    const line = points.map((p, i) => `${i ? 'L' : 'M'}${x(ts[i]).toFixed(1)},${y(p.avg).toFixed(1)}`).join('');
    const hasBand = points.some((p) => p.max !== p.min);
    const band = hasBand
      ? points.map((p, i) => `${i ? 'L' : 'M'}${x(ts[i]).toFixed(1)},${y(p.max).toFixed(1)}`).join('') +
        [...points]
          .reverse()
          .map((p, i) => `L${x(ts[points.length - 1 - i]).toFixed(1)},${y(p.min).toFixed(1)}`)
          .join('') +
        'Z'
      : null;
    const xTicks = [0, 0.33, 0.66, 1].map((f) => t0 + f * (t1 - t0));
    return { ts, x, y, line, band, ticks, xTicks, span: t1 - t0, w };
  }, [points, width, height, sparkline, pad.left, pad.right, pad.top, pad.bottom]);

  const pick = (locX: number) => {
    if (!geo) return;
    let best = 0;
    let dist = Infinity;
    geo.ts.forEach((t, i) => {
      const d = Math.abs(geo.x(t) - locX);
      if (d < dist) {
        dist = d;
        best = i;
      }
    });
    setActive(best);
  };

  const onLayout = (e: LayoutChangeEvent) => setWidth(e.nativeEvent.layout.width);
  const interactive = !sparkline && points.length > 0;
  const p = active !== null ? points[active] : null;

  return (
    <View style={{ gap: Spacing.two }}>
      {interactive ? (
        <View style={styles.readout}>
          {p ? (
            <>
              <Text variant="heading">
                {formatValue(p.avg, digits)} {unit}
              </Text>
              {p.min !== p.max ? (
                <Text variant="caption" color="textSecondary">
                  {formatValue(p.min, digits)} – {formatValue(p.max, digits)}
                </Text>
              ) : null}
              <Text variant="caption" color="textSecondary" style={{ marginLeft: 'auto' }}>
                {formatDateTime(p.at)}
              </Text>
            </>
          ) : (
            <Text variant="caption" color="textSecondary">
              Přejeď po grafu pro zobrazení hodnot
            </Text>
          )}
        </View>
      ) : null}
      <View
        style={{ height, width: '100%' }}
        onLayout={onLayout}
        onStartShouldSetResponder={() => interactive}
        onMoveShouldSetResponder={() => interactive}
        onResponderGrant={(e: GestureResponderEvent) => pick(e.nativeEvent.locationX)}
        onResponderMove={(e: GestureResponderEvent) => pick(e.nativeEvent.locationX)}
        onPointerMove={interactive ? (e) => pick(e.nativeEvent.offsetX) : undefined}
        onPointerLeave={interactive ? () => setActive(null) : undefined}>
        {geo ? (
          <Svg width={width} height={height}>
            {!sparkline &&
              geo.ticks.map((t) => (
                <Line key={`g${t}`} x1={PAD.left} x2={width - PAD.right} y1={geo.y(t)} y2={geo.y(t)} stroke={c.grid} strokeWidth={1} />
              ))}
            {!sparkline &&
              geo.ticks.map((t) => (
                <SvgText
                  key={`l${t}`}
                  x={PAD.left - 6}
                  y={geo.y(t) + 4}
                  fontSize={11}
                  fill={c.textSecondary}
                  textAnchor="end"
                  fontFamily={Fonts.sans}>
                  {formatValue(t, digits)}
                </SvgText>
              ))}
            {!sparkline &&
              geo.xTicks.map((t, i) => (
                <SvgText
                  key={`x${i}`}
                  x={geo.x(t)}
                  y={height - 6}
                  fontSize={11}
                  fill={c.textSecondary}
                  textAnchor={i === 0 ? 'start' : i === geo.xTicks.length - 1 ? 'end' : 'middle'}
                  fontFamily={Fonts.sans}>
                  {formatAxisTime(t, geo.span)}
                </SvgText>
              ))}
            {geo.band && !sparkline ? <Path d={geo.band} fill={c.chartBand} /> : null}
            <Path d={geo.line} stroke={c.accent} strokeWidth={sparkline ? 1.5 : 2} fill="none" strokeLinejoin="round" strokeLinecap="round" />
            {p && active !== null ? (
              <>
                <Line
                  x1={geo.x(geo.ts[active])}
                  x2={geo.x(geo.ts[active])}
                  y1={PAD.top}
                  y2={height - PAD.bottom}
                  stroke={c.textSecondary}
                  strokeDasharray="3 3"
                  strokeWidth={1}
                />
                <Circle cx={geo.x(geo.ts[active])} cy={geo.y(p.avg)} r={5} fill={c.accent} stroke={c.card} strokeWidth={2} />
              </>
            ) : null}
          </Svg>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  readout: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: Spacing.two,
    minHeight: 24,
    borderRadius: Radius.sm,
  },
});
