import { DarkTheme, DefaultTheme, Stack, ThemeProvider } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { useEffect, type ReactNode } from 'react';

import { SettingsProvider, useSettings } from '@/context/settings';
import { WidgetsProvider, useWidgets } from '@/context/widgets';

SplashScreen.preventAutoHideAsync();

export default function RootLayout() {
  return (
    <SettingsProvider>
      <WidgetsProvider>
        <Themed>
          <Stack>
            <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
            <Stack.Screen name="widget/[id]" options={{ title: 'Průběh hodnot', headerBackTitle: 'Zpět' }} />
            <Stack.Screen name="widget/edit" options={{ title: 'Widget', presentation: 'modal' }} />
          </Stack>
        </Themed>
      </WidgetsProvider>
    </SettingsProvider>
  );
}

/** Napoji zvoleny rezim (system / svetly / tmavy) na navigaci a status bar. */
function Themed({ children }: { children: ReactNode }) {
  const { scheme, colors, loaded } = useSettings();
  const widgets = useWidgets();

  useEffect(() => {
    if (loaded && widgets.loaded) SplashScreen.hideAsync();
  }, [loaded, widgets.loaded]);

  const base = scheme === 'dark' ? DarkTheme : DefaultTheme;
  const theme = {
    ...base,
    colors: {
      ...base.colors,
      primary: colors.accent,
      background: colors.background,
      card: colors.card,
      text: colors.text,
      border: colors.border,
    },
  };

  return (
    <ThemeProvider value={theme}>
      <StatusBar style={scheme === 'dark' ? 'light' : 'dark'} />
      {children}
    </ThemeProvider>
  );
}
