/**
 * VideoSync Component - Video player synchronized with subtitle editor
 */
import { useRef, useEffect, useCallback, forwardRef, useImperativeHandle, useMemo } from 'react';
import { Button, Space, Typography } from 'antd';
import { PlayCircleOutlined, PauseOutlined } from '@ant-design/icons';
import { getVideoStreamUrl } from '../../services/api';
import type { SubtitleEntry } from '../../types';

const { Text } = Typography;

interface VideoSyncProps {
  videoFilename: string;
  currentTime: number;
  isPlaying: boolean;
  entries?: SubtitleEntry[];
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

const VideoSync = forwardRef<VideoSyncRef, VideoSyncProps>(({
  videoFilename,
  currentTime,
  isPlaying,
  entries = [],
  onTimeUpdate,
  onPlayingChange,
}, ref) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const isSeekingRef = useRef(false);

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

  const videoUrl = getVideoStreamUrl(videoFilename);

  return (
    <div className="video-sync-container flex flex-col h-full">
      <div className="flex-1 bg-black rounded-lg overflow-hidden relative">
        <video
          ref={videoRef}
          src={videoUrl}
          className="w-full h-full object-contain"
          onTimeUpdate={handleTimeUpdate}
          onPlay={handlePlay}
          onPause={handlePause}
          onClick={togglePlay}
        />
        
        {/* Subtitle overlay */}
        {activeSubtitle && (
          <div className="absolute bottom-0 left-0 right-0 p-4 pointer-events-none">
            <div className="text-center">
              {/* Translation text */}
              <div className="inline-block bg-black/75 text-white px-4 py-2 rounded-lg text-lg leading-relaxed max-w-full">
                {activeSubtitle.text}
              </div>
              {/* Original text (smaller, below) */}
              {activeSubtitle.originalText && (
                <div className="inline-block bg-black/60 text-gray-300 px-3 py-1 rounded-lg text-sm mt-1 max-w-full">
                  {activeSubtitle.originalText}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
      
      <div className="flex items-center justify-between mt-3 px-2">
        <Space>
          <Button
            type="primary"
            icon={isPlaying ? <PauseOutlined /> : <PlayCircleOutlined />}
            onClick={togglePlay}
            size="small"
          >
            {isPlaying ? '暂停' : '播放'}
          </Button>
        </Space>
        
        <Text className="font-mono text-sm">
          {formatTime(currentTime)}
        </Text>
      </div>
    </div>
  );
});

VideoSync.displayName = 'VideoSync';

export default VideoSync;
