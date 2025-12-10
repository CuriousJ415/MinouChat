/**
 * MinouChat Theme Manager
 * Handles light/dark theme toggling with localStorage persistence
 */

const ThemeManager = {
  STORAGE_KEY: 'minouchat-theme',
  THEME_LIGHT: 'light',
  THEME_DARK: 'dark',

  /**
   * Initialize the theme manager
   * Should be called on page load
   */
  init() {
    // Apply saved theme or system preference
    const savedTheme = this.get();
    this.set(savedTheme);

    // Listen for system preference changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
      if (!localStorage.getItem(this.STORAGE_KEY)) {
        this.set(e.matches ? this.THEME_DARK : this.THEME_LIGHT);
      }
    });

    // Set up toggle buttons
    this.setupToggleButtons();
  },

  /**
   * Get the current theme (from storage or system preference)
   * @returns {string} 'light' or 'dark'
   */
  get() {
    const saved = localStorage.getItem(this.STORAGE_KEY);
    if (saved) {
      return saved;
    }
    // Fall back to system preference
    return window.matchMedia('(prefers-color-scheme: dark)').matches
      ? this.THEME_DARK
      : this.THEME_LIGHT;
  },

  /**
   * Set the theme
   * @param {string} theme - 'light' or 'dark'
   */
  set(theme) {
    const validTheme = theme === this.THEME_DARK ? this.THEME_DARK : this.THEME_LIGHT;

    // Update document class
    document.documentElement.classList.remove('theme-light', 'theme-dark');
    document.documentElement.classList.add(`theme-${validTheme}`);

    // Also update body class for compatibility
    document.body.classList.remove('theme-light', 'theme-dark');
    document.body.classList.add(`theme-${validTheme}`);

    // Save to localStorage
    localStorage.setItem(this.STORAGE_KEY, validTheme);

    // Update toggle button icons
    this.updateToggleIcons(validTheme);

    // Dispatch custom event for other components
    window.dispatchEvent(new CustomEvent('themechange', { detail: { theme: validTheme } }));
  },

  /**
   * Toggle between light and dark themes
   */
  toggle() {
    const current = this.get();
    const newTheme = current === this.THEME_DARK ? this.THEME_LIGHT : this.THEME_DARK;
    this.set(newTheme);
    return newTheme;
  },

  /**
   * Check if current theme is dark
   * @returns {boolean}
   */
  isDark() {
    return this.get() === this.THEME_DARK;
  },

  /**
   * Set up click handlers for theme toggle buttons
   */
  setupToggleButtons() {
    document.querySelectorAll('.theme-toggle, [data-theme-toggle]').forEach(button => {
      button.addEventListener('click', (e) => {
        e.preventDefault();
        this.toggle();
      });
    });
  },

  /**
   * Update toggle button icons based on current theme
   * @param {string} theme - Current theme
   */
  updateToggleIcons(theme) {
    document.querySelectorAll('.theme-toggle').forEach(button => {
      const sunIcon = button.querySelector('.icon-sun');
      const moonIcon = button.querySelector('.icon-moon');

      if (sunIcon && moonIcon) {
        if (theme === this.THEME_DARK) {
          sunIcon.style.display = 'none';
          moonIcon.style.display = 'block';
        } else {
          sunIcon.style.display = 'block';
          moonIcon.style.display = 'none';
        }
      }
    });
  }
};

// Immediately apply theme to prevent flash of unstyled content
(function() {
  const saved = localStorage.getItem('minouchat-theme');
  const theme = saved || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  document.documentElement.classList.add('theme-' + theme);
})();

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => ThemeManager.init());
} else {
  ThemeManager.init();
}

// Export for use in other scripts
window.ThemeManager = ThemeManager;
