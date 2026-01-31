/**
 * IndexedDB Service - Draft subtitle storage
 */
import { openDB, DBSchema, IDBPDatabase } from 'idb';
import type { SubtitleEntry } from '../types';

interface SubtitleEditorDB extends DBSchema {
  drafts: {
    key: string;
    value: {
      id: string;
      entries: SubtitleEntry[];
      updatedAt: string;
    };
  };
}

const DB_NAME = 'subtitle-editor';
const DB_VERSION = 1;
const STORE_NAME = 'drafts';
const DRAFT_KEY = 'current-draft';

let dbPromise: Promise<IDBPDatabase<SubtitleEditorDB>> | null = null;

/**
 * Get or create database connection
 */
async function getDB(): Promise<IDBPDatabase<SubtitleEditorDB>> {
  if (!dbPromise) {
    dbPromise = openDB<SubtitleEditorDB>(DB_NAME, DB_VERSION, {
      upgrade(db) {
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          db.createObjectStore(STORE_NAME, { keyPath: 'id' });
        }
      },
    });
  }
  return dbPromise;
}

/**
 * Save subtitle entries as draft to IndexedDB
 */
export async function saveDraft(entries: SubtitleEntry[]): Promise<void> {
  const db = await getDB();
  await db.put(STORE_NAME, {
    id: DRAFT_KEY,
    entries,
    updatedAt: new Date().toISOString(),
  });
}

/**
 * Load draft subtitle entries from IndexedDB
 */
export async function loadDraft(): Promise<SubtitleEntry[] | null> {
  const db = await getDB();
  const draft = await db.get(STORE_NAME, DRAFT_KEY);
  return draft?.entries || null;
}

/**
 * Check if a draft exists in IndexedDB
 */
export async function hasDraft(): Promise<boolean> {
  const db = await getDB();
  const draft = await db.get(STORE_NAME, DRAFT_KEY);
  return !!draft;
}

/**
 * Clear draft from IndexedDB
 */
export async function clearDraft(): Promise<void> {
  const db = await getDB();
  await db.delete(STORE_NAME, DRAFT_KEY);
}

/**
 * Get draft metadata (without full entries)
 */
export async function getDraftInfo(): Promise<{ updatedAt: string; count: number } | null> {
  const db = await getDB();
  const draft = await db.get(STORE_NAME, DRAFT_KEY);
  if (!draft) return null;
  return {
    updatedAt: draft.updatedAt,
    count: draft.entries.length,
  };
}
