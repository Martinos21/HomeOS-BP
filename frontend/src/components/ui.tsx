import Ionicons from '@expo/vector-icons/Ionicons';
import type { ComponentProps, ReactNode } from 'react';
import {
  ActivityIndicator,
  Platform,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text as RNText,
  TextInput,
  View,
  type StyleProp,
  type TextInputProps,
  type TextProps,
  type ViewStyle,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Fonts, MaxContentWidth, Radius, Spacing, type ThemeColor } from '@/constants/theme';
import { useColors } from '@/context/settings';

export type IconName = ComponentProps<typeof Ionicons>['name'];

type Variant = 'title' | 'heading' | 'body' | 'label' | 'caption' | 'value' | 'mono';

export function Text({
  variant = 'body',
  color = 'text',
  style,
  ...rest
}: TextProps & { variant?: Variant; color?: ThemeColor }) {
  const c = useColors();
  return <RNText style={[{ color: c[color], fontFamily: Fonts.sans }, textStyles[variant], style]} {...rest} />;
}

const textStyles = StyleSheet.create({
  title: { fontSize: 28, lineHeight: 34, fontWeight: '700' },
  heading: { fontSize: 17, lineHeight: 22, fontWeight: '600' },
  body: { fontSize: 15, lineHeight: 21, fontWeight: '400' },
  label: { fontSize: 13, lineHeight: 18, fontWeight: '600', letterSpacing: 0.2 },
  caption: { fontSize: 12, lineHeight: 16, fontWeight: '500' },
  value: { fontSize: 30, lineHeight: 36, fontWeight: '700', fontVariant: ['tabular-nums'] },
  mono: { fontSize: 13, lineHeight: 18, fontFamily: Fonts.mono },
});

export function Icon({ name, size = 20, color = 'text' }: { name: IconName; size?: number; color?: ThemeColor }) {
  const c = useColors();
  return <Ionicons name={name} size={size} color={c[color]} />;
}

/** Stranka: scroll, safe area, max. sirka na webu/tabletu. */
export function Screen({
  children,
  title,
  right,
  refreshing,
  onRefresh,
  tabs = true,
}: {
  children: ReactNode;
  title?: string;
  right?: ReactNode;
  refreshing?: boolean;
  onRefresh?: () => void;
  tabs?: boolean;
}) {
  const c = useColors();
  const insets = useSafeAreaInsets();
  // SDK 58: na iOS 26+ je hlavicka Stacku pruhledna (Liquid Glass) a obsah jde pod ni.
  // Na obrazovkach se Stack hlavickou (tabs=false) proto nechame iOS dopocitat
  // horni i dolni odsazeni samo; taby hlavicku nemaji a safe area si resi rucne.
  const iosAutoInsets = !tabs && Platform.OS === 'ios';
  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: c.background }}
      contentInsetAdjustmentBehavior={iosAutoInsets ? 'automatic' : 'never'}
      contentContainerStyle={{
        paddingTop: tabs ? insets.top + Spacing.three : Spacing.three,
        paddingBottom: (iosAutoInsets ? 0 : insets.bottom) + Spacing.five,
        paddingHorizontal: Spacing.three,
        alignItems: 'center',
      }}
      refreshControl={
        onRefresh ? (
          <RefreshControl refreshing={!!refreshing} onRefresh={onRefresh} tintColor={c.textSecondary} />
        ) : undefined
      }>
      <View style={{ width: '100%', maxWidth: MaxContentWidth, gap: Spacing.three }}>
        {title ? (
          <View style={styles.header}>
            <Text variant="title" style={{ flex: 1 }} accessibilityRole="header">
              {title}
            </Text>
            {right}
          </View>
        ) : null}
        {children}
      </View>
    </ScrollView>
  );
}

export function Card({
  children,
  style,
  onPress,
  onLongPress,
  accessibilityLabel,
}: {
  children: ReactNode;
  style?: StyleProp<ViewStyle>;
  onPress?: () => void;
  onLongPress?: () => void;
  accessibilityLabel?: string;
}) {
  const c = useColors();
  const base = [styles.card, { backgroundColor: c.card, borderColor: c.border }];
  if (!onPress) return <View style={[base, style]}>{children}</View>;
  return (
    <Pressable
      onPress={onPress}
      onLongPress={onLongPress}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel}
      style={({ pressed, hovered }: { pressed: boolean; hovered?: boolean }) => [
        base,
        (pressed || hovered) && { backgroundColor: c.cardPressed },
        style,
      ]}>
      {children}
    </Pressable>
  );
}

export function Button({
  label,
  icon,
  onPress,
  variant = 'primary',
  disabled,
  loading,
  compact,
}: {
  label: string;
  icon?: IconName;
  onPress?: () => void;
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  disabled?: boolean;
  loading?: boolean;
  compact?: boolean;
}) {
  const c = useColors();
  const bg =
    variant === 'primary' ? c.accent : variant === 'danger' ? 'transparent' : variant === 'ghost' ? 'transparent' : c.accentSoft;
  const fg: ThemeColor =
    variant === 'primary' ? 'accentText' : variant === 'danger' ? 'danger' : 'accent';
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled || loading}
      accessibilityRole="button"
      accessibilityLabel={label}
      style={({ pressed }) => [
        styles.button,
        compact && styles.buttonCompact,
        { backgroundColor: bg, opacity: disabled ? 0.45 : pressed ? 0.75 : 1 },
        variant === 'danger' && { borderWidth: 1, borderColor: c.danger },
      ]}>
      {loading ? (
        <ActivityIndicator size="small" color={c[fg]} />
      ) : icon ? (
        <Icon name={icon} size={18} color={fg} />
      ) : null}
      <Text variant="label" color={fg}>
        {label}
      </Text>
    </Pressable>
  );
}

export function IconButton({
  icon,
  onPress,
  label,
  color = 'text',
}: {
  icon: IconName;
  onPress: () => void;
  label: string;
  color?: ThemeColor;
}) {
  const c = useColors();
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={label}
      hitSlop={8}
      style={({ pressed }) => [styles.iconButton, { backgroundColor: pressed ? c.cardPressed : 'transparent' }]}>
      <Icon name={icon} size={22} color={color} />
    </Pressable>
  );
}

/** Prepinac s nekolika moznostmi (svetly/tmavy, rozsah grafu, statistika...). */
export function Segmented<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
}) {
  const c = useColors();
  return (
    <View style={[styles.segmented, { backgroundColor: c.background, borderColor: c.border }]} accessibilityRole="tablist">
      {options.map((o) => {
        const active = o.value === value;
        return (
          <Pressable
            key={o.value}
            onPress={() => onChange(o.value)}
            accessibilityRole="tab"
            accessibilityState={{ selected: active }}
            style={[styles.segment, active && { backgroundColor: c.card, borderColor: c.border, borderWidth: 1 }]}>
            <Text variant="label" color={active ? 'text' : 'textSecondary'} numberOfLines={1}>
              {o.label}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

/** Vyber z vetsiho seznamu (zarizeni, hodnoty) jako "chipy". */
export function Chips<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T | null;
  options: { value: T; label: string; icon?: IconName }[];
  onChange: (v: T) => void;
}) {
  const c = useColors();
  return (
    <View style={styles.chips}>
      {options.map((o) => {
        const active = o.value === value;
        return (
          <Pressable
            key={o.value}
            onPress={() => onChange(o.value)}
            accessibilityRole="radio"
            accessibilityState={{ checked: active }}
            style={[
              styles.chip,
              { borderColor: active ? c.accent : c.border, backgroundColor: active ? c.accentSoft : c.card },
            ]}>
            {o.icon ? <Icon name={o.icon} size={16} color={active ? 'accent' : 'textSecondary'} /> : null}
            <Text variant="label" color={active ? 'accent' : 'text'}>
              {o.label}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

export function Field({ label, hint, ...props }: TextInputProps & { label: string; hint?: string }) {
  const c = useColors();
  return (
    <View style={{ gap: Spacing.one }}>
      <Text variant="label" color="textSecondary">
        {label}
      </Text>
      <TextInput
        placeholderTextColor={c.textSecondary}
        autoCapitalize="none"
        autoCorrect={false}
        style={[styles.input, { color: c.text, borderColor: c.border, backgroundColor: c.background }]}
        {...props}
      />
      {hint ? (
        <Text variant="caption" color="textSecondary">
          {hint}
        </Text>
      ) : null}
    </View>
  );
}

export function SectionTitle({ children }: { children: ReactNode }) {
  return (
    <Text variant="label" color="textSecondary" style={{ textTransform: 'uppercase', marginTop: Spacing.two }}>
      {children}
    </Text>
  );
}

/** Radek "popisek ..... hodnota" v nastaveni. */
export function InfoRow({ label, value, icon, last }: { label: string; value: ReactNode; icon?: IconName; last?: boolean }) {
  const c = useColors();
  return (
    <View style={[styles.infoRow, !last && { borderBottomWidth: StyleSheet.hairlineWidth, borderColor: c.border }]}>
      {icon ? <Icon name={icon} size={18} color="textSecondary" /> : null}
      <Text style={{ flex: 1 }}>{label}</Text>
      {typeof value === 'string' ? (
        <Text color="textSecondary" style={{ flexShrink: 1, textAlign: 'right' }} selectable>
          {value}
        </Text>
      ) : (
        value
      )}
    </View>
  );
}

export function Notice({ tone = 'info', text, action }: { tone?: 'info' | 'error'; text: string; action?: ReactNode }) {
  const c = useColors();
  return (
    <View
      style={[
        styles.notice,
        { borderColor: tone === 'error' ? c.danger : c.border, backgroundColor: tone === 'error' ? 'transparent' : c.accentSoft },
      ]}>
      <Icon name={tone === 'error' ? 'alert-circle-outline' : 'information-circle-outline'} color={tone === 'error' ? 'danger' : 'accent'} />
      <Text style={{ flex: 1 }}>{text}</Text>
      {action}
    </View>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two, minHeight: 44 },
  card: { borderRadius: Radius.lg, borderWidth: 1, padding: Spacing.three },
  button: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.two,
    minHeight: 44,
    paddingHorizontal: Spacing.three,
    borderRadius: Radius.md,
  },
  buttonCompact: { minHeight: 36, paddingHorizontal: Spacing.two + 4 },
  iconButton: { width: 44, height: 44, borderRadius: 22, alignItems: 'center', justifyContent: 'center' },
  segmented: { flexDirection: 'row', borderRadius: Radius.md, borderWidth: 1, padding: 3, gap: 3 },
  segment: {
    flex: 1,
    minHeight: 36,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: Radius.sm + 2,
    paddingHorizontal: Spacing.two,
    borderWidth: 1,
    borderColor: 'transparent',
  },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.one + 2,
    minHeight: 38,
    paddingHorizontal: Spacing.three - 4,
    borderRadius: 999,
    borderWidth: 1,
  },
  input: { minHeight: 44, borderWidth: 1, borderRadius: Radius.md, paddingHorizontal: Spacing.three - 4, fontSize: 15 },
  infoRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.three - 4, minHeight: 46, paddingVertical: Spacing.two },
  notice: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two, padding: Spacing.three - 4, borderRadius: Radius.md, borderWidth: 1 },
});
