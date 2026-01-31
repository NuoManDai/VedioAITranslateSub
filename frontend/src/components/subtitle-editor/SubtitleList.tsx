/**
 * SubtitleList Component - Editable list of subtitle entries
 * Professional styling for subtitle editing workflow
 */
import { useCallback, useRef, useEffect } from 'react';
import { Input, Typography, Button, Tooltip } from 'antd';
import { DeleteOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { SubtitleEntry } from '../../types';

const { Text } = Typography;

interface SubtitleListProps {
  entries: SubtitleEntry[];
  currentTime: number;
  selectedIndex: number | null;
  onSelectEntry: (index: number) => void;
  onUpdateEntry: (index: number, changes: Partial<SubtitleEntry>) => void;
  onDeleteEntry?: (index: number) => void;
  onSeekTo: (time: number) => void;
}

/**
 * Parse time string (HH:MM:SS,mmm or MM:SS.mmm) to seconds
 */
function parseTimeString(timeStr: string): number | null {
  // Try HH:MM:SS,mmm format
  const srtMatch = timeStr.match(/^(\d{1,2}):(\d{2}):(\d{2})[,.](\d{3})$/);
  if (srtMatch) {
    const hours = parseInt(srtMatch[1], 10);
    const minutes = parseInt(srtMatch[2], 10);
    const seconds = parseInt(srtMatch[3], 10);
    const ms = parseInt(srtMatch[4], 10);
    return hours * 3600 + minutes * 60 + seconds + ms / 1000;
  }

  // Try MM:SS.mmm format
  const shortMatch = timeStr.match(/^(\d{1,2}):(\d{2})[.,](\d{1,3})$/);
  if (shortMatch) {
    const minutes = parseInt(shortMatch[1], 10);
    const seconds = parseInt(shortMatch[2], 10);
    const ms = parseInt(shortMatch[3].padEnd(3, '0'), 10);
    return minutes * 60 + seconds + ms / 1000;
  }

  // Try MM:SS format
  const simpleMatch = timeStr.match(/^(\d{1,2}):(\d{2})$/);
  if (simpleMatch) {
    const minutes = parseInt(simpleMatch[1], 10);
    const seconds = parseInt(simpleMatch[2], 10);
    return minutes * 60 + seconds;
  }

  return null;
}

/**
 * Format seconds to SRT time string (HH:MM:SS,mmm)
 */
function formatSrtTime(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  const ms = Math.floor((seconds % 1) * 1000);
  return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')},${ms.toString().padStart(3, '0')}`;
}

/**
 * Find active subtitle index based on current time
 */
function findActiveIndex(entries: SubtitleEntry[], time: number): number {
  return entries.findIndex(
    entry => time >= entry.startTime && time <= entry.endTime
  );
}

export default function SubtitleList({
  entries,
  currentTime,
  selectedIndex,
  onSelectEntry,
  onUpdateEntry,
  onDeleteEntry,
  onSeekTo,
}: SubtitleListProps) {
  const { t } = useTranslation();
  const listRef = useRef<HTMLDivElement>(null);
  const activeIndex = findActiveIndex(entries, currentTime);

  // Auto-scroll to active subtitle
  useEffect(() => {
    if (activeIndex >= 0 && listRef.current) {
      const activeElement = listRef.current.querySelector(`[data-index="${activeIndex}"]`);
      if (activeElement) {
        activeElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }, [activeIndex]);

  const handleTimeChange = useCallback((
    index: number,
    field: 'startTime' | 'endTime',
    value: string
  ) => {
    const time = parseTimeString(value);
    if (time !== null) {
      onUpdateEntry(index, { [field]: time });
    }
  }, [onUpdateEntry]);

  const handleTextChange = useCallback((
    index: number,
    field: 'text' | 'originalText',
    value: string
  ) => {
    onUpdateEntry(index, { [field]: value });
  }, [onUpdateEntry]);

  const handleRowClick = useCallback((index: number, entry: SubtitleEntry) => {
    onSelectEntry(index);
    onSeekTo(entry.startTime);
  }, [onSelectEntry, onSeekTo]);

  const handleDelete = useCallback((e: React.MouseEvent, index: number) => {
    e.stopPropagation();
    if (onDeleteEntry) {
      onDeleteEntry(index);
    }
  }, [onDeleteEntry]);

  return (
    <div 
      ref={listRef}
      className="subtitle-list h-full overflow-y-auto bg-gradient-to-b from-slate-50 to-white"
    >
      <div className="space-y-3 p-4">
        {entries.map((entry, index) => {
          const isActive = index === activeIndex;
          const isSelected = index === selectedIndex;
          const duration = (entry.endTime - entry.startTime).toFixed(2);
          
          return (
            <div
              key={entry.index}
              data-index={index}
              className={`
                subtitle-entry rounded-xl border-2 transition-all duration-200 cursor-pointer
                backdrop-blur-sm overflow-hidden
                ${isActive 
                  ? 'border-indigo-500 bg-gradient-to-r from-indigo-50 via-purple-50 to-indigo-50 shadow-lg shadow-indigo-100' 
                  : 'border-slate-200 bg-white hover:border-indigo-300 hover:shadow-md'
                }
                ${isSelected && !isActive ? 'ring-2 ring-indigo-400 ring-offset-1' : ''}
              `}
              onClick={() => handleRowClick(index, entry)}
            >
              {/* Header bar with gradient */}
              <div className={`
                flex items-center gap-3 px-4 py-2.5 border-b
                ${isActive 
                  ? 'bg-gradient-to-r from-indigo-100/80 to-purple-100/80 border-indigo-200/50' 
                  : 'bg-gradient-to-r from-slate-50 to-slate-100/50 border-slate-100'
                }
              `}>
                {/* Index badge */}
                <div className={`
                  w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold
                  ${isActive 
                    ? 'bg-indigo-500 text-white shadow-sm' 
                    : 'bg-slate-200 text-slate-600'
                  }
                `}>
                  {entry.index}
                </div>
                
                {/* Time inputs */}
                <div className="flex items-center gap-2">
                  <ClockCircleOutlined className={`text-xs ${isActive ? 'text-indigo-500' : 'text-slate-400'}`} />
                  <Input
                    key={`start-${index}-${entry.startTime.toFixed(3)}`}
                    size="small"
                    className="w-28 font-mono text-xs rounded-md hover:border-indigo-400 focus:border-indigo-500"
                    defaultValue={formatSrtTime(entry.startTime)}
                    onClick={e => e.stopPropagation()}
                    onBlur={e => handleTimeChange(index, 'startTime', e.target.value)}
                    onPressEnter={e => (e.target as HTMLInputElement).blur()}
                  />
                  
                  <span className={`text-sm font-medium ${isActive ? 'text-indigo-400' : 'text-slate-300'}`}>→</span>
                  
                  <Input
                    key={`end-${index}-${entry.endTime.toFixed(3)}`}
                    size="small"
                    className="w-28 font-mono text-xs rounded-md hover:border-indigo-400 focus:border-indigo-500"
                    defaultValue={formatSrtTime(entry.endTime)}
                    onClick={e => e.stopPropagation()}
                    onBlur={e => handleTimeChange(index, 'endTime', e.target.value)}
                    onPressEnter={e => (e.target as HTMLInputElement).blur()}
                  />
                </div>

                {/* Duration badge */}
                <div className={`
                  px-2 py-0.5 rounded text-xs font-mono
                  ${isActive ? 'bg-indigo-200/60 text-indigo-700' : 'bg-slate-100 text-slate-500'}
                `}>
                  {duration}s
                </div>

                <div className="flex-1" />
                
                {onDeleteEntry && (
                  <Tooltip title={t('deleteSubtitle')} placement="left">
                    <Button
                      type="text"
                      size="small"
                      danger
                      icon={<DeleteOutlined />}
                      className="opacity-40 hover:opacity-100 transition-opacity"
                      onClick={e => handleDelete(e, index)}
                    />
                  </Tooltip>
                )}
              </div>

              {/* Content area */}
              <div className="p-4 space-y-3">
                {/* Translation text */}
                <div>
                  <Text className={`text-xs font-medium mb-1.5 block ${isActive ? 'text-indigo-600' : 'text-slate-500'}`}>
                    {t('translation')}
                  </Text>
                  <Input.TextArea
                    size="small"
                    className="rounded-lg border-slate-200 hover:border-indigo-300 focus:border-indigo-500 resize-none"
                    placeholder={t('enterTranslation')}
                    value={entry.text}
                    autoSize={{ minRows: 1, maxRows: 4 }}
                    onClick={e => e.stopPropagation()}
                    onChange={e => handleTextChange(index, 'text', e.target.value)}
                  />
                </div>

                {/* Original text */}
                {entry.originalText !== undefined && (
                  <div>
                    <Text className="text-xs font-medium text-slate-400 mb-1.5 block">
                      {t('originalText')}
                    </Text>
                    <Input.TextArea
                      size="small"
                      className="rounded-lg border-slate-200 bg-slate-50/50 text-slate-600 hover:border-slate-300 focus:border-slate-400 resize-none"
                      placeholder={t('enterOriginal')}
                      value={entry.originalText || ''}
                      autoSize={{ minRows: 1, maxRows: 3 }}
                      onClick={e => e.stopPropagation()}
                      onChange={e => handleTextChange(index, 'originalText', e.target.value)}
                    />
                  </div>
                )}
              </div>
            </div>
          );
        })}
        
        {/* Empty state */}
        {entries.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-slate-400">
            <ClockCircleOutlined className="text-4xl mb-3 opacity-30" />
            <Text className="text-slate-400">{t('noSubtitles')}</Text>
          </div>
        )}
      </div>
    </div>
  );
}
