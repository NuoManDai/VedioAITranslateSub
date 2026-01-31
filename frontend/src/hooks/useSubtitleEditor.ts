/**
 * useSubtitleEditor Hook - State management for subtitle editor
 */
import { useState, useCallback, useEffect, useRef } from 'react';
import { message } from 'antd';
import type { SubtitleEntry, SubtitleDataResponse } from '../types';
import { 
  getSubtitles, 
  saveSubtitles, 
  mergeSubtitlesToVideo,
  backupSubtitles,
  hasSubtitleBackup,
  restoreSubtitles,
} from '../services/subtitleApi';
import { saveDraft, loadDraft, clearDraft, hasDraft } from '../services/indexeddb';

interface UseSubtitleEditorReturn {
  // State
  entries: SubtitleEntry[];
  currentTime: number;
  isPlaying: boolean;
  selectedIndex: number | null;
  isDirty: boolean;
  isLoading: boolean;
  isSaving: boolean;
  isMerging: boolean;
  isRestoring: boolean;
  hasBackup: boolean;
  filesInfo: SubtitleDataResponse['files'] | null;

  // Actions
  loadSubtitles: () => Promise<void>;
  updateEntry: (index: number, changes: Partial<SubtitleEntry>) => void;
  addEntry: (startTime: number, endTime: number) => void;
  deleteEntry: (index: number) => void;
  saveToServer: () => Promise<boolean>;
  saveDraftLocal: () => Promise<void>;
  mergeVideo: () => Promise<boolean>;
  restoreToOriginal: () => Promise<boolean>;
  setCurrentTime: (time: number) => void;
  setIsPlaying: (playing: boolean) => void;
  setSelectedIndex: (index: number | null) => void;
  seekTo: (time: number) => void;
  discardDraft: () => Promise<void>;
}

const AUTO_SAVE_INTERVAL = 30000; // 30 seconds

export function useSubtitleEditor(): UseSubtitleEditorReturn {
  const [entries, setEntries] = useState<SubtitleEntry[]>([]);
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [isDirty, setIsDirty] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isMerging, setIsMerging] = useState(false);
  const [isRestoring, setIsRestoring] = useState(false);
  const [hasBackup, setHasBackup] = useState(false);
  const [filesInfo, setFilesInfo] = useState<SubtitleDataResponse['files'] | null>(null);

  const seekCallbackRef = useRef<((time: number) => void) | null>(null);

  // Load subtitles from API or draft
  const loadSubtitles = useCallback(async () => {
    setIsLoading(true);
    try {
      // Always check backup status first
      const backupStatus = await hasSubtitleBackup();
      setHasBackup(backupStatus.hasBackup);

      // Check for draft first
      const hasDraftData = await hasDraft();
      if (hasDraftData) {
        const draftEntries = await loadDraft();
        if (draftEntries && draftEntries.length > 0) {
          // Ask user if they want to restore draft
          setEntries(draftEntries);
          setIsDirty(true);
          message.info('已恢复上次编辑的草稿');
          
          // Still fetch file info from server
          const data = await getSubtitles();
          setFilesInfo(data.files);

          // Create backup if not exists (use server data for backup)
          if (!backupStatus.hasBackup && data.entries.length > 0) {
            await backupSubtitles();
            setHasBackup(true);
          }
          
          setIsLoading(false);
          return;
        }
      }

      // Load from server
      const data = await getSubtitles();
      setEntries(data.entries);
      setFilesInfo(data.files);
      setIsDirty(false);

      // Create backup if not exists
      if (!backupStatus.hasBackup && data.entries.length > 0) {
        await backupSubtitles();
        setHasBackup(true);
      }
    } catch (error) {
      message.error(error instanceof Error ? error.message : '加载字幕失败');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Update a single entry
  const updateEntry = useCallback((index: number, changes: Partial<SubtitleEntry>) => {
    setEntries(prev => prev.map((entry, i) => 
      i === index ? { ...entry, ...changes } : entry
    ));
    setIsDirty(true);
  }, []);

  // Add a new subtitle entry
  const addEntry = useCallback((startTime: number, endTime: number) => {
    setEntries(prev => {
      const newIndex = prev.length > 0 ? Math.max(...prev.map(e => e.index)) + 1 : 1;
      const newEntry: SubtitleEntry = {
        index: newIndex,
        startTime,
        endTime,
        text: '',
        originalText: '',
      };
      // Insert and sort by startTime
      return [...prev, newEntry].sort((a, b) => a.startTime - b.startTime);
    });
    setIsDirty(true);
  }, []);

  // Delete a subtitle entry
  const deleteEntry = useCallback((index: number) => {
    setEntries(prev => prev.filter((_, i) => i !== index));
    setSelectedIndex(null);
    setIsDirty(true);
  }, []);

  // Save to server
  const saveToServer = useCallback(async (): Promise<boolean> => {
    setIsSaving(true);
    try {
      await saveSubtitles(entries);
      await clearDraft();
      setIsDirty(false);
      message.success('字幕已保存');
      return true;
    } catch (error) {
      message.error(error instanceof Error ? error.message : '保存失败');
      return false;
    } finally {
      setIsSaving(false);
    }
  }, [entries]);

  // Save draft to IndexedDB
  const saveDraftLocal = useCallback(async () => {
    if (entries.length > 0 && isDirty) {
      await saveDraft(entries);
    }
  }, [entries, isDirty]);

  // Merge subtitles to video
  const mergeVideo = useCallback(async (): Promise<boolean> => {
    setIsMerging(true);
    try {
      const result = await mergeSubtitlesToVideo();
      if (result.success) {
        message.success('字幕已合并到视频');
        return true;
      } else {
        message.error(result.error || '合并失败');
        return false;
      }
    } catch (error) {
      message.error(error instanceof Error ? error.message : '合并失败');
      return false;
    } finally {
      setIsMerging(false);
    }
  }, []);

  // Restore subtitles to original (from backup)
  const restoreToOriginal = useCallback(async (): Promise<boolean> => {
    setIsRestoring(true);
    try {
      const result = await restoreSubtitles();
      if (result.success) {
        // Clear draft
        await clearDraft();
        // Reload subtitles from server
        const data = await getSubtitles();
        setEntries(data.entries);
        setFilesInfo(data.files);
        setIsDirty(false);
        message.success('字幕已还原到原始状态');
        return true;
      } else {
        message.error(result.error || '还原失败');
        return false;
      }
    } catch (error) {
      message.error(error instanceof Error ? error.message : '还原失败');
      return false;
    } finally {
      setIsRestoring(false);
    }
  }, []);

  // Seek to time (used by video player)
  const seekTo = useCallback((time: number) => {
    setCurrentTime(time);
    if (seekCallbackRef.current) {
      seekCallbackRef.current(time);
    }
  }, []);

  // Discard draft
  const discardDraft = useCallback(async () => {
    await clearDraft();
    setIsDirty(false);
    // Reload from server
    await loadSubtitles();
  }, [loadSubtitles]);

  // Auto-save draft every 30 seconds
  useEffect(() => {
    if (!isDirty) return;

    const interval = setInterval(() => {
      saveDraftLocal();
    }, AUTO_SAVE_INTERVAL);

    return () => clearInterval(interval);
  }, [isDirty, saveDraftLocal]);

  // Save draft on unmount
  useEffect(() => {
    return () => {
      if (isDirty && entries.length > 0) {
        saveDraft(entries);
      }
    };
  }, [isDirty, entries]);

  return {
    // State
    entries,
    currentTime,
    isPlaying,
    selectedIndex,
    isDirty,
    isLoading,
    isSaving,
    isMerging,
    isRestoring,
    hasBackup,
    filesInfo,

    // Actions
    loadSubtitles,
    updateEntry,
    addEntry,
    deleteEntry,
    saveToServer,
    saveDraftLocal,
    mergeVideo,
    restoreToOriginal,
    setCurrentTime,
    setIsPlaying,
    setSelectedIndex,
    seekTo,
    discardDraft,
  };
}
