/**
 * VideoSync Component - Video player synchronized with subtitle editor
 * Redesigned with modern, elegant UI
 */
import { useRef, useEffect, useCallback, forwardRef, useImperativeHandle, useMemo } from 'react';
import { Typography, Slider } from 'antd';
import { PlayCircleFilled, PauseCircleFilled, SoundOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { getVideoStreamUrl } from '../../services/api';
import type { SubtitleEntry, SubtitleDisplayStyle } from '../../types';

const { Text } = Typography;

/**
 * Default subtitle display styles
 * These match the backend FFmpeg subtitle burn-in styles
 */
export const DEFAULT_SUBTITLE_STYLE: SubtitleDisplayStyle = {
  translation: {
    fontSize: 18,
    fontColor: '#FFFFFF',
    bgColor: 'rgba(0,0,0,0.75)',
    outlineColor: '#000000',
    outlineWidth: 1,
  },
  original: {
    fontSize: 14,
    fontColor: '#CCCCCC',
    bgColor: 'rgba(0,0,0,0.6)',
    outlineColor: '#000000',
    outlineWidth: 1,
  },
  layout: {
    marginBottom: 40,
    lineSpacing: 8,
  },
};

interface VideoSyncProps {
  videoFilename: string;
  currentTime: number;
  isPlaying: boolean;
  entries?: SubtitleEntry[];
  subtitleStyle?: SubtitleDisplayStyle;
  onTimeUpdate: (time: number) => void;
  onPlayingChange: (playing: boolean) => void;
}

export interface VideoSyncRef {
  seekTo: (time: number) => void;
}

/**
 * Format seconds to display time string (MM:SS.mmm)
 */
function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  const ms = Math.floor((seconds % 1) * 1000);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
}

/**
 * Format seconds to compact time string (MM:SS)
 */
function formatTimeCompact(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

const VideoSync = forwardRef<VideoSyncRef, VideoSyncProps>(({
  videoFilename,
  currentTime,
  isPlaying,
  entries = [],
  subtitleStyle = DEFAULT_SUBTITLE_STYLE,
  onTimeUpdate,
  onPlayingChange,
}, ref) => {
  const { t } = useTranslation();
  const videoRef = useRef<HTMLVideoElement>(null);
  const isSeekingRef = useRef(false);
  const durationRef = useRef(0);

  // Expose seekTo method via ref
  useImperativeHandle(ref, () => ({
    seekTo: (time: number) => {
      if (videoRef.current) {
        isSeekingRef.current = true;
        videoRef.current.currentTime = time;
        setTimeout(() => {
          isSeekingRef.current = false;
        }, 100);
      }
    },
  }), []);

  // Handle play/pause state
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    if (isPlaying && video.paused) {
      video.play().catch(() => {
        onPlayingChange(false);
      });
    } else if (!isPlaying && !video.paused) {
      video.pause();
    }
  }, [isPlaying, onPlayingChange]);

  // Handle time updates from video
  const handleTimeUpdate = useCallback(() => {
    if (videoRef.current && !isSeekingRef.current) {
      onTimeUpdate(videoRef.current.currentTime);
    }
  }, [onTimeUpdate]);

  // Handle video loaded metadata
  const handleLoadedMetadata = useCallback(() => {
    if (videoRef.current) {
      durationRef.current = videoRef.current.duration;
    }
  }, []);

  // Handle video events
  const handlePlay = useCallback(() => {
    onPlayingChange(true);
  }, [onPlayingChange]);

  const handlePause = useCallback(() => {
    onPlayingChange(false);
  }, [onPlayingChange]);

  const togglePlay = useCallback(() => {
    onPlayingChange(!isPlaying);
  }, [isPlaying, onPlayingChange]);

  // Find the current active subtitle based on time
  const activeSubtitle = useMemo(() => {
    return entries.find(
      entry => currentTime >= entry.startTime && currentTime <= entry.endTime
    );
  }, [entries, currentTime]);

  // Calculate progress percentage
  const progressPercent = durationRef.current > 0 
    ? (currentTime / durationRef.current) * 100 
    : 0;

  const videoUrl = getVideoStreamUrl(videoFilename);

  return (
    <div className="video-sync-container flex flex-col h-full">
      {/* Video Container with rounded corners and shadow */}
      <div className="flex-1 relative group rounded-xl overflow-hidden bg-black shadow-2xl ring-1 ring-white/10">
        <video
          ref={videoRef}
          src={videoUrl}
          className="w-full h-full object-contain"
          onTimeUpdate={handleTimeUpdate}
          onLoadedMetadata={handleLoadedMetadata}
          onPlay={handlePlay}
          onPause={handlePause}
          onClick={togglePlay}
          muted
        />
        
        {/* Play/Pause overlay button - shows on hover */}
        <div 
          className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200 cursor-pointer"
          onClick={togglePlay}
        >
          <div className="w-16 h-16 rounded-full bg-black/40 backdrop-blur-sm flex items-center justify-center transform transition-transform hover:scale-110">
            {isPlaying ? (
              <PauseCircleFilled className="text-4xl text-white/90" />
            ) : (
              <PlayCircleFilled className="text-4xl text-white/90" />
            )}
          </div>
        </div>
        
        {/* Subtitle overlay */}
        {activeSubtitle && (
          <div 
            className="absolute left-0 right-0 pointer-events-none flex flex-col items-center px-4"
            style={{ bottom: `${subtitleStyle.layout.marginBottom}px` }}
          >
            {/* Translation text (main subtitle) */}
            <div 
              className="inline-block px-4 py-2 rounded-lg leading-relaxed max-w-[90%] text-center backdrop-blur-sm"
              style={{
                fontSize: `${subtitleStyle.translation.fontSize}px`,
                color: subtitleStyle.translation.fontColor,
                backgroundColor: subtitleStyle.translation.bgColor,
                textShadow: `0 1px 2px rgba(0,0,0,0.8), ${subtitleStyle.translation.outlineWidth}px ${subtitleStyle.translation.outlineWidth}px 0 ${subtitleStyle.translation.outlineColor}`,
              }}
            >
              {activeSubtitle.text}
            </div>
            {/* Original text (secondary, below translation) */}
            {activeSubtitle.originalText && (
              <div 
                className="inline-block px-3 py-1.5 rounded-lg max-w-[90%] text-center backdrop-blur-sm"
                style={{
                  fontSize: `${subtitleStyle.original.fontSize}px`,
                  color: subtitleStyle.original.fontColor,
                  backgroundColor: subtitleStyle.original.bgColor,
                  textShadow: `0 1px 2px rgba(0,0,0,0.8), ${subtitleStyle.original.outlineWidth}px ${subtitleStyle.original.outlineWidth}px 0 ${subtitleStyle.original.outlineColor}`,
                  marginTop: `${subtitleStyle.layout.lineSpacing}px`,
                }}
              >
                {activeSubtitle.originalText}
              </div>
            )}
          </div>
        )}

        {/* Muted indicator */}
        <div className="absolute top-3 right-3 px-2 py-1 rounded-md bg-black/50 backdrop-blur-sm flex items-center gap-1.5">
          <SoundOutlined className="text-white/60 text-xs" />
          <span className="text-white/60 text-xs">{t('muted') || '静音'}</span>
        </div>
      </div>
      
      {/* Controls Bar - Modern floating design */}
      <div className="mt-4 px-1">
        {/* Progress bar */}
        <div className="relative h-1.5 bg-white/20 rounded-full overflow-hidden cursor-pointer group/progress mb-3">
          <div 
            className="absolute left-0 top-0 h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all"
            style={{ width: `${progressPercent}%` }}
          />
          {/* Hover indicator */}
          <div 
            className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-white rounded-full shadow-lg opacity-0 group-hover/progress:opacity-100 transition-opacity"
            style={{ left: `calc(${progressPercent}% - 6px)` }}
          />
        </div>

        {/* Time and Play controls */}
        <div className="flex items-center justify-between">
          {/* Play button */}
          <button
            onClick={togglePlay}
            className="flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 text-white font-medium text-sm shadow-lg shadow-indigo-500/30 hover:shadow-indigo-500/50 hover:scale-105 transition-all"
          >
            {isPlaying ? (
              <>
                <PauseCircleFilled className="text-base" />
                <span>{t('pause') || '暂停'}</span>
              </>
            ) : (
              <>
                <PlayCircleFilled className="text-base" />
                <span>{t('play') || '播放'}</span>
              </>
            )}
          </button>
          
          {/* Time display */}
          <div className="flex items-center gap-2">
            <Text className="font-mono text-sm text-white/90 bg-white/10 px-3 py-1.5 rounded-lg backdrop-blur-sm">
              {formatTime(currentTime)}
            </Text>
            {durationRef.current > 0 && (
              <>
                <span className="text-white/40">/</span>
                <Text className="font-mono text-xs text-white/50">
                  {formatTimeCompact(durationRef.current)}
                </Text>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
});

VideoSync.displayName = 'VideoSync';

export default VideoSync;
