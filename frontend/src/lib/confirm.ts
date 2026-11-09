import { Alert, Platform } from 'react-native';

/** Potvrzovaci dialog, ktery funguje i na webu (Alert.alert tam tlacitka neumi). */
export function confirm(title: string, message: string, okLabel = 'Smazat'): Promise<boolean> {
  if (Platform.OS === 'web') {
    return Promise.resolve(typeof window !== 'undefined' && window.confirm(`${title}\n\n${message}`));
  }
  return new Promise((resolve) =>
    Alert.alert(title, message, [
      { text: 'Zrušit', style: 'cancel', onPress: () => resolve(false) },
      { text: okLabel, style: 'destructive', onPress: () => resolve(true) },
    ]),
  );
}
