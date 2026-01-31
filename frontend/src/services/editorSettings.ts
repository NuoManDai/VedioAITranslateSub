/**
 * Editor Settings Service - localStorage-based settings for subtitle editor
 */

const STORAGE_KEY = 'subtitle-editor-settings';

export interface EditorSettings {
  /** Whether to auto-stop playback at segment end when using Space key */
  autoStopAtSegmentEnd: boolean;
}

const DEFAULT_SETTINGS: EditorSettings = {
  autoStopAtSegmentEnd: true,
};

/**
 * Load editor settings from localStorage
 */
export function loadEditorSettings(): EditorSettings {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      return { ...DEFAULT_SETTINGS, ...parsed };
    }
  } catch (e) {
    console.warn('Failed to load editor settings:', e);
  }
  return { ...DEFAULT_SETTINGS };
}

/**
 * Save editor settings to localStorage
 */
export function saveEditorSettings(settings: Partial<EditorSettings>): EditorSettings {
  const current = loadEditorSettings();
  const updated = { ...current, ...settings };
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  } catch (e) {
    console.warn('Failed to save editor settings:', e);
  }
  return updated;
}

/**
 * Reset editor settings to defaults
 */
export function resetEditorSettings(): EditorSettings {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch (e) {
    console.warn('Failed to reset editor settings:', e);
  }
  return { ...DEFAULT_SETTINGS };
}
