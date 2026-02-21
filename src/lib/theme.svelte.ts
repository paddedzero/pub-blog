type Theme = 'light' | 'dark' | 'system';

function createTheme() {
  let theme = $state<Theme>('system');
  let mediaQuery: MediaQueryList | undefined;
  let isListeningToSystem = false;

  function updateDom(isDark: boolean) {
    const contains = document.documentElement.classList.contains('dark');
    if (isDark && !contains) {
      document.documentElement.classList.add('dark');
    } else if (!isDark && contains) {
      document.documentElement.classList.remove('dark');
    }
  }

  const onSystemThemeChange = (e: MediaQueryListEvent) => {
    if (isListeningToSystem) {
      updateDom(e.matches);
    }
  };

  function applyTheme(newTheme: Theme) {
    if (typeof window === 'undefined') return;

    localStorage.setItem('theme', newTheme);

    if (!mediaQuery) {
      mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    }

    // Always try to remove first to avoid duplicates or when switching mode
    mediaQuery.removeEventListener('change', onSystemThemeChange);

    if (newTheme === 'system') {
      isListeningToSystem = true;
      updateDom(mediaQuery.matches);
      mediaQuery.addEventListener('change', onSystemThemeChange);
    } else {
      isListeningToSystem = false;
      updateDom(newTheme === 'dark');
    }
  }

  if (typeof window !== 'undefined') {
    const savedTheme = localStorage.getItem('theme') as Theme | null;
    const initialTheme =
      savedTheme && ['light', 'dark', 'system'].includes(savedTheme) ? savedTheme : 'system';
    theme = initialTheme;
    applyTheme(initialTheme);
  }

  function toggle() {
    if (theme === 'system') theme = 'light';
    else if (theme === 'light') theme = 'dark';
    else theme = 'system';
    applyTheme(theme);
  }

  function set(newTheme: Theme) {
    theme = newTheme;
    applyTheme(newTheme);
  }

  return {
    get current() {
      return theme;
    },
    toggle,
    set,
  };
}

export const theme = createTheme();
