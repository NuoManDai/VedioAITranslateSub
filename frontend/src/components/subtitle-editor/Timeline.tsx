/**
 * Timeline Component - Audio waveform with subtitle regions
 */
import { useRef, useEffect, useCallback, forwardRef, useImperativeHandle, useState } from 'react';
import { Typography, Spin } from 'antd';
import WaveSurfer from 'wavesurfer.js';
import RegionsPlugin, { Region } from 'wavesurfer.js/dist/plugins/regions.js';
import TimelinePlugin from 'wavesurfer.js/dist/plugins/timeline.js';
import type { SubtitleEntry } from '../../types';
import { getAudioStreamUrl } from '../../services/subtitleApi';

const { Text } = Typography;

interface TimelineProps {
  entries: SubtitleEntry[];
  currentTime: number;
  isPlaying: boolean;
  onSeek: (time: number) => void;
  onUpdateEntry: (index: number, changes: Partial<SubtitleEntry>) => void;
  onAddEntry?: (startTime: number, endTime: number) => void;
  onPlayingChange: (playing: boolean) => void;
  selectedIndex?: number | null;
  onSelectEntry?: (index: number) => void;
}

export interface TimelineRef {
  seekTo: (time: number) => void;
}

const Timeline = forwardRef<TimelineRef, TimelineProps>(({
  entries,
  currentTime,
  isPlaying,
  onSeek,
  onUpdateEntry,
  onAddEntry,
  onPlayingChange,
  selectedIndex,
  onSelectEntry,
}, ref) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const wavesurferRef = useRef<WaveSurfer | null>(null);
  const regionsRef = useRef<RegionsPlugin | null>(null);
  const isSeekingRef = useRef(false);
  const isLoadingRef = useRef(true);
  const isUpdatingRegionsRef = useRef(false);
  const regionMapRef = useRef<Map<string, number>>(new Map());
  const indexToRegionRef = useRef<Map<number, string>>(new Map());
  const [zoomLevel, setZoomLevel] = useState(50);
  const [cursorTime, setCursorTime] = useState<number | null>(null);

  // Expose seekTo method via ref
  useImperativeHandle(ref, () => ({
    seekTo: (time: number) => {
      if (wavesurferRef.current) {
        const duration = wavesurferRef.current.getDuration();
        if (duration > 0) {
          isSeekingRef.current = true;
          wavesurferRef.current.seekTo(time / duration);
          setTimeout(() => {
            isSeekingRef.current = false;
          }, 100);
        }
      }
    },
  }), []);

  // Generate a unique color for each subtitle entry
  const getRegionColor = useCallback((index: number): string => {
    const colors = [
      'rgba(102, 126, 234, 0.3)',  // purple
      'rgba(76, 175, 80, 0.3)',    // green
      'rgba(255, 152, 0, 0.3)',    // orange
      'rgba(233, 30, 99, 0.3)',    // pink
      'rgba(0, 188, 212, 0.3)',    // cyan
    ];
    return colors[index % colors.length];
  }, []);

  // Initialize WaveSurfer
  useEffect(() => {
    if (!containerRef.current) return;

    const ws = WaveSurfer.create({
      container: containerRef.current,
      waveColor: '#e0e0e0',
      progressColor: '#667eea',
      cursorColor: '#764ba2',
      cursorWidth: 2,
      height: 100,
      barWidth: 2,
      barGap: 1,
      barRadius: 2,
      minPxPerSec: zoomLevel,
    });

    // Register regions plugin with drag selection for creating new subtitles
    const regions = ws.registerPlugin(RegionsPlugin.create());
    
    // Register timeline plugin for time markers
    ws.registerPlugin(TimelinePlugin.create({
      height: 20,
      timeInterval: 1,
      primaryLabelInterval: 5,
      style: {
        fontSize: '10px',
        color: '#666',
      },
    }));
    
    wavesurferRef.current = ws;
    regionsRef.current = regions;

    // Load audio
    const audioUrl = getAudioStreamUrl();
    ws.load(audioUrl);

    // Event handlers
    ws.on('ready', () => {
      isLoadingRef.current = false;
      // Add regions for each subtitle entry
      updateRegions();
    });

    ws.on('audioprocess', () => {
      if (!isSeekingRef.current && wavesurferRef.current) {
        const time = wavesurferRef.current.getCurrentTime();
        onSeek(time);
      }
    });

    ws.on('seeking', () => {
      if (wavesurferRef.current) {
        const time = wavesurferRef.current.getCurrentTime();
        onSeek(time);
      }
    });

    ws.on('play', () => {
      onPlayingChange(true);
    });

    ws.on('pause', () => {
      onPlayingChange(false);
    });

    ws.on('click', () => {
      if (wavesurferRef.current) {
        const time = wavesurferRef.current.getCurrentTime();
        onSeek(time);
      }
    });

    // Handle region updates (drag/resize existing regions)
    regions.on('region-updated', (region: Region) => {
      const entryIndex = regionMapRef.current.get(region.id);
      if (entryIndex !== undefined) {
        onUpdateEntry(entryIndex, {
          startTime: region.start,
          endTime: region.end,
        });
      }
    });

    // Handle region click (select subtitle)
    regions.on('region-clicked', (region: Region, e: MouseEvent) => {
      e.stopPropagation();
      const entryIndex = regionMapRef.current.get(region.id);
      if (entryIndex !== undefined && onSelectEntry) {
        onSelectEntry(entryIndex);
      }
    });

    // Handle new region creation by dragging on empty space
    regions.enableDragSelection({
      color: 'rgba(102, 126, 234, 0.3)',
    });

    regions.on('region-created', (region: Region) => {
      // Ignore regions created during updateRegions()
      if (isUpdatingRegionsRef.current) {
        return;
      }
      // Check if this is a new region (not one we created from entries)
      if (!regionMapRef.current.has(region.id)) {
        // This is a user-created region via drag
        if (onAddEntry && region.end - region.start >= 0.1) {
          onAddEntry(region.start, region.end);
        }
        // Remove the region since we'll recreate it from entries
        region.remove();
      }
    });

    return () => {
      ws.destroy();
    };
  }, []); // Empty deps - only run once

  // Update regions when entries change
  const updateRegions = useCallback(() => {
    const regions = regionsRef.current;
    if (!regions || isLoadingRef.current) return;

    // Set flag to prevent region-created event from triggering onAddEntry
    isUpdatingRegionsRef.current = true;

    // Clear existing regions
    regions.clearRegions();
    regionMapRef.current.clear();
    indexToRegionRef.current.clear();

    // Add new regions
    entries.forEach((entry, index) => {
      const isSelected = index === selectedIndex;
      const region = regions.addRegion({
        start: entry.startTime,
        end: entry.endTime,
        color: isSelected ? 'rgba(102, 126, 234, 0.5)' : getRegionColor(index),
        drag: true,
        resize: true,
      });
      regionMapRef.current.set(region.id, index);
      indexToRegionRef.current.set(index, region.id);
    });

    // Reset flag after all regions are added
    isUpdatingRegionsRef.current = false;
  }, [entries, getRegionColor, selectedIndex]);

  // Update regions when entries change
  useEffect(() => {
    if (!isLoadingRef.current) {
      updateRegions();
    }
  }, [entries, updateRegions, selectedIndex]);

  // Sync play state with video
  useEffect(() => {
    const ws = wavesurferRef.current;
    if (!ws || isLoadingRef.current) return;

    if (isPlaying && !ws.isPlaying()) {
      ws.play();
    } else if (!isPlaying && ws.isPlaying()) {
      ws.pause();
    }
  }, [isPlaying]);

  // Sync current time with video (only when seeking from outside)
  useEffect(() => {
    const ws = wavesurferRef.current;
    if (!ws || isLoadingRef.current) return;

    const duration = ws.getDuration();
    if (duration > 0) {
      const currentWsTime = ws.getCurrentTime();
      // Only sync if difference is significant (>0.5s)
      if (Math.abs(currentWsTime - currentTime) > 0.5) {
        isSeekingRef.current = true;
        ws.seekTo(currentTime / duration);
        setTimeout(() => {
          isSeekingRef.current = false;
        }, 100);
      }
    }
  }, [currentTime]);

  // Mouse wheel zoom
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      const ws = wavesurferRef.current;
      if (!ws) return;

      const delta = e.deltaY > 0 ? -10 : 10;
      const newZoom = Math.max(10, Math.min(500, zoomLevel + delta));
      setZoomLevel(newZoom);
      ws.zoom(newZoom);
    };

    container.addEventListener('wheel', handleWheel, { passive: false });
    return () => container.removeEventListener('wheel', handleWheel);
  }, [zoomLevel]);

  // Mouse move to show cursor time
  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const ws = wavesurferRef.current;
    if (!ws || isLoadingRef.current) return;

    const container = containerRef.current;
    if (!container) return;

    const rect = container.getBoundingClientRect();
    const scrollLeft = container.scrollLeft || 0;
    const x = e.clientX - rect.left + scrollLeft;
    const duration = ws.getDuration();
    const pixelsPerSecond = ws.options.minPxPerSec || 50;
    const time = x / pixelsPerSecond;
    
    if (time >= 0 && time <= duration) {
      setCursorTime(time);
    }
  }, []);

  const handleMouseLeave = useCallback(() => {
    setCursorTime(null);
  }, []);

  // Format time for display
  const formatTimeShort = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 1000);
    return `${mins}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
  };

  return (
    <div className="timeline-container relative">
      <div className="flex items-center justify-between mb-2">
        <Text className="text-sm text-gray-500">音频波形 & 时间轴</Text>
        <div className="flex items-center gap-4">
          {cursorTime !== null && (
            <Text className="text-xs text-purple-600 font-mono">
              {formatTimeShort(cursorTime)}
            </Text>
          )}
          <Text className="text-xs text-gray-400">
            拖拽空白区域创建字幕 | 滚轮缩放 | 拖拽色块边缘调整时间
          </Text>
        </div>
      </div>
      
      <div 
        ref={containerRef}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        className="w-full rounded-lg bg-gray-50 border border-gray-200 overflow-x-auto"
        style={{ cursor: 'crosshair' }}
      />
      
      {isLoadingRef.current && (
        <div className="absolute inset-0 flex items-center justify-center bg-white/80">
          <Spin tip="加载音频波形..." />
        </div>
      )}
    </div>
  );
});

Timeline.displayName = 'Timeline';

export default Timeline;
