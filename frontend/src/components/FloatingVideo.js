// frontend/src/components/FloatingVideo.js
import React, { useEffect, useRef } from 'react';
import Draggable from 'react-draggable';
import useVideoStore from '../store/useVideoStore';
import mpegts from 'mpegts.js';

export default function FloatingVideo() {
  const { isVisible, streamUrl, hideVideo } = useVideoStore();
  const videoRef = useRef(null);
  const playerRef = useRef(null);

  useEffect(() => {
    if (!isVisible || !streamUrl) {
      return;
    }

    // If the browser supports MSE for live playback, initialize mpegts.js
    if (mpegts.getFeatureList().mseLivePlayback) {
      const player = mpegts.createPlayer({
        type: 'mpegts',
        url: streamUrl,
        isLive: true,
        // You can include other custom MPEGTS.js config fields here, e.g.:
        // cors: true,
        // withCredentials: false,
      });

      player.attachMediaElement(videoRef.current);
      player.load();
      player.play();

      // Store player instance so we can clean up later
      playerRef.current = player;
    }

    // Cleanup when component unmounts or streamUrl changes
    return () => {
      if (playerRef.current) {
        playerRef.current.destroy();
        playerRef.current = null;
      }
    };
  }, [isVisible, streamUrl]);

  // If the floating video is hidden or no URL is selected, do not render
  if (!isVisible || !streamUrl) {
    return null;
  }

  return (
    <Draggable>
      <div
        style={{
          position: 'fixed',
          bottom: '20px',
          right: '20px',
          width: '320px',
          zIndex: 9999,
          backgroundColor: '#333',
          borderRadius: '8px',
          overflow: 'hidden',
          boxShadow: '0 2px 10px rgba(0,0,0,0.7)',
        }}
      >
        {/* Simple header row with a close button */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'flex-end',
            padding: '4px',
          }}
        >
          <button
            onClick={hideVideo}
            style={{
              background: 'red',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '0.8rem',
              padding: '2px 8px',
            }}
          >
            X
          </button>
        </div>

        {/* The <video> element used by mpegts.js */}
        <video
          ref={videoRef}
          controls
          style={{ width: '100%', height: '180px', backgroundColor: '#000' }}
        />
      </div>
    </Draggable>
  );
}
