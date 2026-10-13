import { React, run } from 'uebersicht';

export const refreshFrequency = 1000;

export const command = `python3 "$HOME/Library/Application Support/Übersicht/widgets/nowplaying.widget/get_song.py" 2>/dev/null || python3 "nowplaying.widget/get_song.py" 2>/dev/null || python3 "ytmusic.widget/get_song.py"`;

const STORAGE_KEY = 'nowplaying_widget_position';
const STORAGE_SIZE_KEY = 'nowplaying_widget_size_preset';
const STORAGE_RATINGS_KEY = 'nowplaying_widget_ratings';
const SCREEN_MARGIN = 2;

const getInitialPosition = () => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY) || localStorage.getItem('ytmusic_widget_position');
    if (saved) {
      const parsed = JSON.parse(saved);
      if (typeof parsed.x === 'number' && typeof parsed.y === 'number') {
        const maxX = Math.max(SCREEN_MARGIN, (window.innerWidth || 1920) - 340);
        const maxY = Math.max(SCREEN_MARGIN, (window.innerHeight || 1080) - 180);
        return {
          x: Math.max(SCREEN_MARGIN, Math.min(maxX, parsed.x)),
          y: Math.max(SCREEN_MARGIN, Math.min(maxY, parsed.y)),
        };
      }
    }
  } catch (e) {}
  return { x: 50, y: 50 };
};

const getInitialSizePreset = () => {
  try {
    const saved = localStorage.getItem(STORAGE_SIZE_KEY);
    if (saved === 'small' || saved === 'medium' || saved === 'large') {
      return saved;
    }
  } catch (e) {}
  return 'medium';
};

const getInitialRatings = () => {
  try {
    const saved = localStorage.getItem(STORAGE_RATINGS_KEY);
    if (saved) return JSON.parse(saved);
  } catch (e) {}
  return {};
};

const initialPos = getInitialPosition();
const initialPreset = getInitialSizePreset();
const initialRatings = getInitialRatings();

export const initialState = {
  x: initialPos.x,
  y: initialPos.y,
  sizePreset: initialPreset,
  contextMenu: null,
  isDragging: false,
  dragStartX: 0,
  dragStartY: 0,
  startPosX: 0,
  startPosY: 0,
  cardWidth: initialPreset === 'small' ? 154 : 300,
  cardHeight: initialPreset === 'small' ? 154 : (initialPreset === 'large' ? 435 : 154),
  data: { playing: false, streams: [] },
  activeStreamIndex: 0,
  ratings: initialRatings,
  error: null,
};

export const updateState = (event, previousState) => {
  if (!previousState) return initialState;

  if (event.type === 'UB/COMMAND_RAN') {
    if (event.error) {
      return { ...previousState, error: event.error };
    }
    try {
      const parsed = JSON.parse(event.output || '{}');
      parsed.clientReceivedAt = Date.now();
      let updatedRatings = previousState.ratings || {};

      const streams = (parsed.streams && parsed.streams.length > 0)
        ? parsed.streams
        : (parsed.title ? [parsed] : []);

      for (const s of streams) {
        if (s.title) {
          const key = `${s.title}___${s.artist || ''}`.toLowerCase();
          if (s.rating !== undefined && s.rating !== null) {
            if (s.rating !== 'none') {
              updatedRatings = { ...updatedRatings, [key]: s.rating };
            } else {
              const copy = { ...updatedRatings };
              delete copy[key];
              updatedRatings = copy;
            }
          }
        }
      }

      const maxIdx = Math.max(0, streams.length - 1);
      const activeIdx = Math.min(maxIdx, previousState.activeStreamIndex || 0);

      return {
        ...previousState,
        activeStreamIndex: activeIdx,
        data: parsed,
        ratings: updatedRatings,
        error: null,
      };
    } catch (err) {
      return {
        ...previousState,
        error: err.message,
      };
    }
  }

  if (event.type === 'SET_STREAM_INDEX') {
    return {
      ...previousState,
      activeStreamIndex: event.index,
    };
  }

  if (event.type === 'SET_RATING') {
    const updatedRatings = { ...(previousState.ratings || {}) };
    if (event.trackKey) {
      if (event.rating && event.rating !== 'none') {
        updatedRatings[event.trackKey] = event.rating;
      } else {
        delete updatedRatings[event.trackKey];
      }
      try {
        localStorage.setItem(STORAGE_RATINGS_KEY, JSON.stringify(updatedRatings));
      } catch (e) {}
    }

    let updatedData = previousState.data;
    if (updatedData) {
      const currentStreams = updatedData.streams && updatedData.streams.length > 0
        ? updatedData.streams
        : (updatedData.title ? [updatedData] : []);

      const newStreams = currentStreams.map((s, idx) => {
        if (idx === (previousState.activeStreamIndex || 0) || (event.streamId && s.id === event.streamId)) {
          return { ...s, rating: event.rating === 'none' ? null : event.rating };
        }
        return s;
      });

      updatedData = {
        ...updatedData,
        streams: newStreams,
        rating: event.rating === 'none' ? null : event.rating,
      };
    }

    return {
      ...previousState,
      ratings: updatedRatings,
      data: updatedData,
    };
  }

  if (event.type === 'OPTIMISTIC_TOGGLE_PLAY') {
    if (!previousState.data || !previousState.data.playing) return previousState;
    const streams = previousState.data.streams && previousState.data.streams.length > 0
      ? previousState.data.streams
      : [previousState.data];

    const streamIdx = event.streamIndex ?? (previousState.activeStreamIndex || 0);
    const targetStream = streams[streamIdx] || streams[0];
    const currentRate = targetStream.rate ?? 1;
    const nextRate = currentRate === 1 ? 0 : 1;
    let nextElapsed = targetStream.elapsed || 0;
    if (nextRate === 0) {
      const delta = (Date.now() - (targetStream.clientReceivedAt || previousState.data.clientReceivedAt || Date.now())) / 1000;
      nextElapsed = Math.min(
        targetStream.duration || 0,
        nextElapsed + Math.max(0, delta)
      );
    }

    const updatedStreams = streams.map((s, idx) => {
      if (idx === streamIdx) {
        return {
          ...s,
          rate: nextRate,
          elapsed: nextElapsed,
          clientReceivedAt: Date.now(),
        };
      }
      return s;
    });

    return {
      ...previousState,
      data: {
        ...previousState.data,
        rate: streamIdx === (previousState.activeStreamIndex || 0) ? nextRate : previousState.data.rate,
        streams: updatedStreams,
      },
    };
  }

  if (event.type === 'TRACK_CHANGE_PENDING') {
    if (!previousState.data || !previousState.data.playing) return previousState;
    const streams = previousState.data.streams && previousState.data.streams.length > 0
      ? previousState.data.streams
      : [previousState.data];

    const streamIdx = event.streamIndex ?? (previousState.activeStreamIndex || 0);
    const updatedStreams = streams.map((s, idx) => {
      if (idx === streamIdx) {
        return {
          ...s,
          elapsed: 0,
          clientReceivedAt: Date.now(),
        };
      }
      return s;
    });

    return {
      ...previousState,
      data: {
        ...previousState.data,
        elapsed: streamIdx === (previousState.activeStreamIndex || 0) ? 0 : previousState.data.elapsed,
        streams: updatedStreams,
      },
    };
  }

  if (event.type === 'TICK') {
    if (!previousState.data || !previousState.data.playing || previousState.data.rate === 0) {
      return previousState;
    }
    return {
      ...previousState,
      tick: event.now,
    };
  }

  if (event.type === 'START_DRAG') {
    return {
      ...previousState,
      contextMenu: null,
      isDragging: true,
      dragStartX: event.clientX,
      dragStartY: event.clientY,
      startPosX: previousState.x,
      startPosY: previousState.y,
      cardWidth: event.cardWidth || previousState.cardWidth || 300,
      cardHeight: event.cardHeight || previousState.cardHeight || 160,
    };
  }

  if (event.type === 'MOVE_DRAG' && previousState.isDragging) {
    const deltaX = event.clientX - previousState.dragStartX;
    const deltaY = event.clientY - previousState.dragStartY;
    const cardWidth = previousState.cardWidth || 300;
    const cardHeight = previousState.cardHeight || 160;

    const maxX = Math.max(SCREEN_MARGIN, window.innerWidth - cardWidth - SCREEN_MARGIN);
    const maxY = Math.max(SCREEN_MARGIN, window.innerHeight - cardHeight - SCREEN_MARGIN);

    const newX = Math.max(SCREEN_MARGIN, Math.min(maxX, previousState.startPosX + deltaX));
    const newY = Math.max(SCREEN_MARGIN, Math.min(maxY, previousState.startPosY + deltaY));

    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ x: newX, y: newY }));
    } catch (e) {}

    return {
      ...previousState,
      x: newX,
      y: newY,
    };
  }

  if (event.type === 'END_DRAG') {
    return {
      ...previousState,
      isDragging: false,
    };
  }

  if (event.type === 'SET_SIZE_PRESET') {
    try {
      localStorage.setItem(STORAGE_SIZE_KEY, event.preset);
    } catch (e) {}

    const newW = event.preset === 'small' ? 154 : 300;
    const newH = event.preset === 'small' ? 154 : (event.preset === 'large' ? 435 : 154);
    const maxX = Math.max(SCREEN_MARGIN, (window.innerWidth || 1920) - newW - SCREEN_MARGIN);
    const maxY = Math.max(SCREEN_MARGIN, (window.innerHeight || 1080) - newH - SCREEN_MARGIN);

    const clampedX = Math.max(SCREEN_MARGIN, Math.min(maxX, previousState.x));
    const clampedY = Math.max(SCREEN_MARGIN, Math.min(maxY, previousState.y));

    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ x: clampedX, y: clampedY }));
    } catch (e) {}

    return {
      ...previousState,
      sizePreset: event.preset,
      cardWidth: newW,
      cardHeight: newH,
      x: clampedX,
      y: clampedY,
      contextMenu: null,
    };
  }

  if (event.type === 'OPEN_CONTEXT_MENU') {
    return {
      ...previousState,
      contextMenu: { x: event.x, y: event.y },
    };
  }

  if (event.type === 'CLOSE_CONTEXT_MENU') {
    return {
      ...previousState,
      contextMenu: null,
    };
  }

  return previousState;
};

const formatTime = (secs) => {
  if (!secs || isNaN(secs) || secs < 0) return '0:00';
  const m = Math.floor(secs / 60);
  const s = Math.floor(secs % 60);
  return `${m}:${s < 10 ? '0' : ''}${s}`;
};

let currentDispatch = null;
if (typeof window !== 'undefined' && !window.__nowplaying_ticker_started) {
  window.__nowplaying_ticker_started = true;
  setInterval(() => {
    if (currentDispatch) {
      currentDispatch({ type: 'TICK', now: Date.now() });
    }
  }, 500);
}

export const render = (state, dispatch) => {
  currentDispatch = dispatch;
  const {
    data,
    error,
    x = 50,
    y = 50,
    isDragging,
    sizePreset = 'medium',
    contextMenu = null,
  } = state || {};

  const handleMouseDown = (e) => {
    if (e.button !== 0) return;
    if (e.target.closest('button') || e.target.closest('[data-interactive="true"]')) return;

    e.preventDefault();
    const rect = e.currentTarget ? e.currentTarget.getBoundingClientRect() : null;
    const defaultW = sizePreset === 'small' ? 154 : 300;
    const defaultH = sizePreset === 'small' ? 154 : (sizePreset === 'large' ? 435 : 154);
    const cardWidth = rect ? rect.width : defaultW;
    const cardHeight = rect ? rect.height : defaultH;

    dispatch({
      type: 'START_DRAG',
      clientX: e.clientX,
      clientY: e.clientY,
      cardWidth,
      cardHeight,
    });

    const handleMouseMove = (moveEvent) => {
      dispatch({ type: 'MOVE_DRAG', clientX: moveEvent.clientX, clientY: moveEvent.clientY });
    };

    const handleMouseUp = () => {
      dispatch({ type: 'END_DRAG' });
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
  };

  const handleContextMenu = (e) => {
    e.preventDefault();
    e.stopPropagation();
    const menuW = 175;
    const menuH = 145;
    const maxX = (window.innerWidth || 1920) - menuW - 12;
    const maxY = (window.innerHeight || 1080) - menuH - 12;
    dispatch({
      type: 'OPEN_CONTEXT_MENU',
      x: Math.max(12, Math.min(maxX, e.clientX)),
      y: Math.max(12, Math.min(maxY, e.clientY)),
    });
  };

  const streams = (data && data.streams && data.streams.length > 0)
    ? data.streams
    : (data && data.title ? [data] : []);
  const activeStreamIndex = Math.min(Math.max(0, streams.length - 1), state?.activeStreamIndex || 0);
  const currentStream = streams[activeStreamIndex] || data || {};

  const isPlaying = Boolean(currentStream && currentStream.title && currentStream.title !== 'Nothing Playing');
  const isPaused = Boolean(isPlaying && currentStream.rate === 0);

  const duration = currentStream?.duration || 0;
  const baseElapsed = currentStream?.elapsed || 0;
  const timeSinceUpdate = (Date.now() - (currentStream?.clientReceivedAt || data?.clientReceivedAt || Date.now())) / 1000;
  const elapsed = (isPlaying && !isPaused && duration > 0)
    ? Math.min(duration, baseElapsed + Math.max(0, timeSinceUpdate))
    : baseElapsed;
  const progressPercent = duration > 0 ? Math.min(100, Math.max(0, (elapsed / duration) * 100)) : 0;

  const title = isPlaying ? currentStream.title : (error ? 'Widget Error' : 'Nothing Playing');
  const artist = isPlaying ? (currentStream.artist || 'Unknown Artist') : (error ? error : 'Playback Idle');
  const album = isPlaying ? (currentStream.album || '') : '';
  const appName = currentStream.appName || '';
  const bundleId = currentStream.bundleId || '';
  const streamId = currentStream.id || '';
  const supportsRating = currentStream.supportsRating ?? false;

  const positionStyle = {
    position: 'absolute',
    top: `${y}px`,
    left: `${x}px`,
    zIndex: 1000,
    cursor: isDragging ? 'grabbing' : 'grab',
    userSelect: 'none',
    WebkitUserSelect: 'none',
    transition: isDragging ? 'none' : 'box-shadow 0.2s ease',
  };

  const trackKey = (currentStream && currentStream.title)
    ? `${currentStream.title}___${currentStream.artist || ''}`.toLowerCase()
    : '';

  const ratings = state?.ratings || {};
  const currentRating = (currentStream && currentStream.rating !== undefined && currentStream.rating !== null)
    ? (currentStream.rating === 'none' ? null : currentStream.rating)
    : (trackKey ? ratings[trackKey] : null);

  const isLiked = currentRating === 'liked';
  const isDisliked = currentRating === 'disliked';

  const handleControl = (action, e) => {
    e.stopPropagation();
    if (!isPlaying) return;
    if (action === 'togglePlayPause') {
      dispatch({ type: 'OPTIMISTIC_TOGGLE_PLAY', streamIndex: activeStreamIndex });
    } else if (action === 'next' || action === 'previous') {
      dispatch({ type: 'TRACK_CHANGE_PENDING', streamIndex: activeStreamIndex });
    }
    const pyScript = '$HOME/Library/Application Support/Übersicht/widgets/nowplaying.widget/media_control.py';
    const pyScriptFallback = 'nowplaying.widget/media_control.py';
    const escapedAction = JSON.stringify(action);
    const escapedId = JSON.stringify(streamId || '');
    const escapedApp = JSON.stringify(appName || '');
    const escapedBundle = JSON.stringify(bundleId || '');
    const escapedKey = JSON.stringify(trackKey || '');
    run(`python3 "${pyScript}" ${escapedAction} ${escapedId} ${escapedApp} ${escapedBundle} ${escapedKey} 2>/dev/null || python3 "${pyScriptFallback}" ${escapedAction} ${escapedId} ${escapedApp} ${escapedBundle} ${escapedKey} 2>/dev/null`);
  };

  const handleRating = (action, e) => {
    e.stopPropagation();
    if (!isPlaying) return;

    // Do NOT optimistically set the color!
    // Execute media_control.py. Only if the stream supports rating and succeeds, update state.
    const pyScript = '$HOME/Library/Application Support/Übersicht/widgets/nowplaying.widget/media_control.py';
    const pyScriptFallback = 'nowplaying.widget/media_control.py';
    const escapedAction = JSON.stringify(action);
    const escapedId = JSON.stringify(streamId || '');
    const escapedApp = JSON.stringify(appName || '');
    const escapedBundle = JSON.stringify(bundleId || '');
    const escapedKey = JSON.stringify(trackKey || '');

    run(
      `python3 "${pyScript}" ${escapedAction} ${escapedId} ${escapedApp} ${escapedBundle} ${escapedKey} 2>/dev/null || python3 "${pyScriptFallback}" ${escapedAction} ${escapedId} ${escapedApp} ${escapedBundle} ${escapedKey} 2>/dev/null`,
      (err, output) => {
        if (err || !output) return;
        try {
          const res = JSON.parse(output.trim());
          if (res && res.success) {
            const nextRating = res.rating === 'none' ? null : res.rating;
            dispatch({ type: 'SET_RATING', trackKey, rating: nextRating, streamId });
          }
        } catch (e) {}
      }
    );
  };

  const renderStreamCarousel = (isSmall = false) => {
    if (!streams || streams.length <= 1) return null;

    const btnSize = isSmall ? '20px' : '24px';
    const chevronSize = isSmall ? 10 : 13;
    const dotHeight = isSmall ? 5 : 6;
    const dotActiveWidth = isSmall ? 14 : 18;
    const dotInactiveWidth = isSmall ? 5 : 6;

    return (
      <div
        data-interactive="true"
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          userSelect: 'none',
          WebkitUserSelect: 'none',
          margin: isSmall ? '1px auto' : '2px auto',
          width: '100%',
        }}
        onClick={(e) => e.stopPropagation()}
        onMouseDown={(e) => e.stopPropagation()}
      >
        {/* Symmetric, fixed-structure carousel pill */}
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: isSmall ? '6px' : '8px',
            padding: isSmall ? '2px 6px' : '3px 8px',
            borderRadius: '14px',
            backgroundColor: 'rgba(255, 255, 255, 0.08)',
            border: '1px solid rgba(255, 255, 255, 0.12)',
            backdropFilter: 'blur(12px)',
            WebkitBackdropFilter: 'blur(12px)',
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.25)',
          }}
        >
          {/* Previous Stream Button */}
          <button
            data-interactive="true"
            style={{
              width: btnSize,
              height: btnSize,
              borderRadius: '50%',
              background: 'rgba(255, 255, 255, 0.06)',
              border: 'none',
              color: 'rgba(255, 255, 255, 0.85)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              outline: 'none',
              padding: 0,
              transition: 'background 0.15s ease, transform 0.1s ease',
            }}
            onClick={(e) => {
              e.stopPropagation();
              const nextIdx = (activeStreamIndex - 1 + streams.length) % streams.length;
              dispatch({ type: 'SET_STREAM_INDEX', index: nextIdx });
            }}
            title="Previous stream"
          >
            <svg width={chevronSize} height={chevronSize} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="15 18 9 12 15 6" />
            </svg>
          </button>

          {/* Dots Indicator */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', padding: '0 2px' }}>
            {streams.map((s, idx) => {
              const isActive = idx === activeStreamIndex;
              return (
                <div
                  key={s.id || idx}
                  data-interactive="true"
                  style={{
                    width: `${isActive ? dotActiveWidth : dotInactiveWidth}px`,
                    height: `${dotHeight}px`,
                    borderRadius: '3px',
                    backgroundColor: isActive ? '#FFFFFF' : 'rgba(255, 255, 255, 0.35)',
                    cursor: 'pointer',
                    transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
                  }}
                  onClick={(e) => {
                    e.stopPropagation();
                    dispatch({ type: 'SET_STREAM_INDEX', index: idx });
                  }}
                  title={`${s.appName || 'Stream'} (${idx + 1}/${streams.length})`}
                />
              );
            })}
          </div>

          {/* Next Stream Button */}
          <button
            data-interactive="true"
            style={{
              width: btnSize,
              height: btnSize,
              borderRadius: '50%',
              background: 'rgba(255, 255, 255, 0.06)',
              border: 'none',
              color: 'rgba(255, 255, 255, 0.85)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              outline: 'none',
              padding: 0,
              transition: 'background 0.15s ease, transform 0.1s ease',
            }}
            onClick={(e) => {
              e.stopPropagation();
              const nextIdx = (activeStreamIndex + 1) % streams.length;
              dispatch({ type: 'SET_STREAM_INDEX', index: nextIdx });
            }}
            title="Next stream"
          >
            <svg width={chevronSize} height={chevronSize} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="9 18 15 12 9 6" />
            </svg>
          </button>
        </div>

        {/* Stable Sub-Label below the pill: shows app name & stream count */}
        <div
          style={{
            fontSize: isSmall ? '8.5px' : '9.5px',
            fontWeight: '600',
            color: 'rgba(255, 255, 255, 0.55)',
            textAlign: 'center',
            letterSpacing: '0.2px',
            lineHeight: '1.2',
            marginTop: '2px',
            height: isSmall ? '11px' : '13px',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            maxWidth: isSmall ? '130px' : '260px',
          }}
          title={`${appName} (${activeStreamIndex + 1}/${streams.length})`}
        >
          {appName ? `${appName} (${activeStreamIndex + 1}/${streams.length})` : `Stream ${activeStreamIndex + 1} of ${streams.length}`}
        </div>
      </div>
    );
  };

  const renderLikeBtn = (customStyle = {}, iconSize = 14) => (
    <button
      data-interactive="true"
      style={{
        ...controlBtnStyle,
        ...customStyle,
        color: isLiked ? '#78b856' : 'rgba(255, 255, 255, 0.85)',
        background: customStyle.background || 'rgba(255, 255, 255, 0.08)',
        border: customStyle.border || '1px solid rgba(255, 255, 255, 0.1)',
        boxShadow: 'none',
        opacity: isPlaying ? 1 : 0.45,
        cursor: isPlaying ? 'pointer' : 'default',
      }}
      onClick={(e) => handleRating('like', e)}
      onMouseDown={(e) => e.stopPropagation()}
      title={isLiked ? 'Unlike' : 'Like'}
    >
      <svg width={iconSize} height={iconSize} viewBox="0 0 24 24" fill="currentColor">
        {isLiked ? (
          <path d="M1 21h4V9H1v12zm22-11c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L14.17 1 7.59 7.59C7.22 7.95 7 8.45 7 9v10c0 1.1.9 2 2 2h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23.14-.47.14-.73v-2z" />
        ) : (
          <path d="M9 21h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23.14-.47.14-.73v-2c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L14.17 1 7.58 7.59C7.22 7.95 7 8.45 7 9v10c0 1.1.9 2 2 2zM9 9l4.34-4.34L12 10h9v2l-3 7H9V9zM1 9h4v12H1z" />
        )}
      </svg>
    </button>
  );

  const renderDislikeBtn = (customStyle = {}, iconSize = 14) => (
    <button
      data-interactive="true"
      style={{
        ...controlBtnStyle,
        ...customStyle,
        color: isDisliked ? '#d75444' : 'rgba(255, 255, 255, 0.85)',
        background: customStyle.background || 'rgba(255, 255, 255, 0.08)',
        border: customStyle.border || '1px solid rgba(255, 255, 255, 0.1)',
        boxShadow: 'none',
        opacity: isPlaying ? 1 : 0.45,
        cursor: isPlaying ? 'pointer' : 'default',
      }}
      onClick={(e) => handleRating('dislike', e)}
      onMouseDown={(e) => e.stopPropagation()}
      title={isDisliked ? 'Remove Dislike' : 'Dislike'}
    >
      <svg width={iconSize} height={iconSize} viewBox="0 0 24 24" fill="currentColor">
        {isDisliked ? (
          <path d="M15 3H6c-.83 0-1.54.5-1.84 1.22l-3.02 7.05c-.09.23-.14.47-.14.73v2c0 1.1.9 2 2 2h6.31l-.95 4.57-.03.32c0 .41.17.79.44 1.06L9.83 23l6.59-6.59c.37-.36.58-.86.58-1.41V5c0-1.1-.9-2-2-2zm4 0v12h4V3h-4z" />
        ) : (
          <path d="M15 3H6c-.83 0-1.54.5-1.84 1.22l-3.02 7.05c-.09.23-.14.47-.14.73v2c0 1.1.9 2 2 2h6.31l-.95 4.57-.03.32c0 .41.17.79.44 1.06L9.83 23l6.59-6.59c.37-.36.58-.86.58-1.41V5c0-1.1-.9-2-2-2zm0 12l-4.34 4.34L12 14H3v-2l3-7h9v10zm4-12h4v12h-4z" />
        )}
      </svg>
    </button>
  );

  return (
    <React.Fragment>
      <div
        style={positionStyle}
        onMouseDown={handleMouseDown}
        onContextMenu={handleContextMenu}
      >
        {sizePreset === 'small' ? (
          /* ========================================= */
          /* SMALL PRESET (~1:1 Aspect Ratio, 154x154) */
          /* ========================================= */
          <div style={smallCardStyle}>
            {/* Artwork 56x56 */}
            <div style={smallArtworkContainerStyle}>
              {isPlaying && currentStream?.artwork ? (
                <img src={currentStream.artwork} alt="Album Art" style={artworkImageStyle} />
              ) : (
                <div style={artworkFallbackStyle}>
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.6)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M9 18V5l12-2v13" />
                    <circle cx="6" cy="18" r="3" />
                    <circle cx="18" cy="16" r="3" />
                  </svg>
                </div>
              )}
            </div>

            {/* Song Metadata */}
            <div style={{ width: '100%', textAlign: 'center', overflow: 'hidden', margin: '2px 0' }}>
              <div
                style={{
                  fontSize: '11px',
                  fontWeight: '600',
                  color: '#FFFFFF',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  lineHeight: '1.25',
                }}
                title={title}
              >
                {title}
              </div>
              <div
                style={{
                  fontSize: '9.5px',
                  fontWeight: '500',
                  color: 'rgba(255, 255, 255, 0.65)',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  marginTop: '1px',
                }}
                title={artist}
              >
                {artist}
              </div>
            </div>

            {/* Mini Progress */}
            <div style={{ width: '100%', height: '3px', borderRadius: '2px', backgroundColor: 'rgba(255, 255, 255, 0.15)', overflow: 'hidden' }}>
              <div
                style={{
                  width: isPlaying && duration > 0 ? `${progressPercent}%` : '0%',
                  height: '100%',
                  backgroundColor: 'rgba(255, 255, 255, 0.75)',
                  borderRadius: '2px',
                  transition: 'width 0.3s ease',
                }}
              />
            </div>

            {/* Stream Switcher (if multiple streams) */}
            {renderStreamCarousel(true)}

            {/* Mini Controls */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '5px' }}>
              {renderDislikeBtn({ width: '20px', height: '20px' }, 11)}
              <button
                data-interactive="true"
                style={{ ...smallControlBtnStyle, width: '22px', height: '22px' }}
                onClick={(e) => handleControl('previous', e)}
                onMouseDown={(e) => e.stopPropagation()}
                title="Previous"
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M6 6h2v12H6zm3.5 6l8.5 6V6z" />
                </svg>
              </button>
              <button
                data-interactive="true"
                style={{ ...smallPlayPauseBtnStyle, width: '26px', height: '26px' }}
                onClick={(e) => handleControl('togglePlayPause', e)}
                onMouseDown={(e) => e.stopPropagation()}
                title={isPlaying && !isPaused ? 'Pause' : 'Play'}
              >
                {isPlaying && !isPaused ? (
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="#000000">
                    <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
                  </svg>
                ) : (
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="#000000">
                    <path d="M8 5v14l11-7z" />
                  </svg>
                )}
              </button>
              <button
                data-interactive="true"
                style={{ ...smallControlBtnStyle, width: '22px', height: '22px' }}
                onClick={(e) => handleControl('next', e)}
                onMouseDown={(e) => e.stopPropagation()}
                title="Next"
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z" />
                </svg>
              </button>
              {renderLikeBtn({ width: '20px', height: '20px' }, 11)}
            </div>
          </div>
        ) : sizePreset === 'large' ? (
          /* ================================================= */
          /* LARGE PRESET (Large Album Art 268x268, 300x~435) */
          /* ================================================= */
          <div style={largeCardStyle}>
            {/* Big 268x268 Album Art */}
            <div style={largeArtworkContainerStyle}>
              {isPlaying && currentStream?.artwork ? (
                <img src={currentStream.artwork} alt="Album Art" style={artworkImageStyle} />
              ) : (
                <div style={{ ...artworkFallbackStyle, backgroundColor: 'rgba(255, 255, 255, 0.05)' }}>
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.4)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M9 18V5l12-2v13" />
                    <circle cx="6" cy="18" r="3" />
                    <circle cx="18" cy="16" r="3" />
                  </svg>
                </div>
              )}
            </div>

            {/* Metadata */}
            <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <div
                style={{
                  fontSize: '15px',
                  fontWeight: '700',
                  color: '#FFFFFF',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  letterSpacing: '-0.3px',
                  lineHeight: '1.25',
                }}
                title={title}
              >
                {title}
              </div>
              <div
                style={{
                  fontSize: '12.5px',
                  fontWeight: '500',
                  color: 'rgba(255, 255, 255, 0.72)',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  marginTop: '2px',
                }}
                title={artist}
              >
                {artist}
              </div>
              {isPlaying && album && album !== title ? (
                <div
                  style={{
                    fontSize: '11px',
                    color: 'rgba(255, 255, 255, 0.42)',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    marginTop: '1px',
                  }}
                  title={album}
                >
                  {album}
                </div>
              ) : (
                <div style={{ fontSize: '11px', color: 'rgba(255, 255, 255, 0.28)', marginTop: '1px' }}>
                  {isPlaying ? '' : (error ? 'Check connection' : 'No track active')}
                </div>
              )}
            </div>

            {/* Progress Bar */}
            <div style={progressSectionStyle}>
              <div style={progressBarTrackStyle}>
                <div
                  style={{
                    ...progressBarFillStyle,
                    width: isPlaying && duration > 0 ? `${progressPercent}%` : '0%',
                  }}
                />
              </div>
              <div style={progressTimesStyle}>
                <span>{isPlaying ? formatTime(elapsed) : '0:00'}</span>
                <span>{isPlaying && duration > 0 ? formatTime(duration) : '0:00'}</span>
              </div>
            </div>

            {/* Stream Switcher (if multiple streams) */}
            {renderStreamCarousel(false)}

            {/* Large Controls */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '14px', marginTop: '2px' }}>
              {renderDislikeBtn({ width: '30px', height: '30px' }, 15)}
              <button
                data-interactive="true"
                style={{ ...controlBtnStyle, width: '34px', height: '34px' }}
                onClick={(e) => handleControl('previous', e)}
                onMouseDown={(e) => e.stopPropagation()}
                title="Previous Track"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M6 6h2v12H6zm3.5 6l8.5 6V6z" />
                </svg>
              </button>
              <button
                data-interactive="true"
                style={{ ...playPauseBtnStyle, width: '40px', height: '40px' }}
                onClick={(e) => handleControl('togglePlayPause', e)}
                onMouseDown={(e) => e.stopPropagation()}
                title={isPlaying && !isPaused ? 'Pause' : 'Play'}
              >
                {isPlaying && !isPaused ? (
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="#000000">
                    <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
                  </svg>
                ) : (
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="#000000">
                    <path d="M8 5v14l11-7z" />
                  </svg>
                )}
              </button>
              <button
                data-interactive="true"
                style={{ ...controlBtnStyle, width: '34px', height: '34px' }}
                onClick={(e) => handleControl('next', e)}
                onMouseDown={(e) => e.stopPropagation()}
                title="Next Track"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z" />
                </svg>
              </button>
              {renderLikeBtn({ width: '30px', height: '30px' }, 15)}
            </div>
          </div>
        ) : (
          /* =================================== */
          /* MEDIUM PRESET (Standard Card, 300x154) */
          /* =================================== */
          <div style={cardStyle}>
            {/* Top Section: Artwork + Info */}
            <div style={topRowStyle}>
              <div style={artworkContainerStyle}>
                {isPlaying && currentStream?.artwork ? (
                  <img src={currentStream.artwork} alt="Album Art" style={artworkImageStyle} />
                ) : (
                  <div style={artworkFallbackStyle}>
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.6)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M9 18V5l12-2v13" />
                      <circle cx="6" cy="18" r="3" />
                      <circle cx="18" cy="16" r="3" />
                    </svg>
                  </div>
                )}
              </div>

              <div style={metaContainerStyle}>
                <div style={titleStyle} title={title}>
                  {title}
                </div>
                <div style={artistStyle} title={artist}>
                  {artist}
                </div>
                {isPlaying && album && album !== title ? (
                  <div style={albumStyle} title={album}>
                    {album}
                  </div>
                ) : (
                  <div style={{ ...albumStyle, opacity: 0.5 }}>
                    {isPlaying ? '' : (error ? 'Check connection' : 'No track active')}
                  </div>
                )}
              </div>
            </div>

            {/* Middle Section: Progress Bar */}
            <div style={progressSectionStyle}>
              <div style={progressBarTrackStyle}>
                <div
                  style={{
                    ...progressBarFillStyle,
                    width: isPlaying && duration > 0 ? `${progressPercent}%` : '0%',
                  }}
                />
              </div>
              <div style={progressTimesStyle}>
                <span>{isPlaying ? formatTime(elapsed) : '0:00'}</span>
                <span>{isPlaying && duration > 0 ? formatTime(duration) : '0:00'}</span>
              </div>
            </div>

            {/* Stream Switcher (if multiple streams) */}
            {renderStreamCarousel(false)}

            {/* Bottom Section: Media Controls */}
            <div style={{ ...controlsRowStyle, gap: '12px' }}>
              {renderDislikeBtn({ width: '28px', height: '28px' }, 14)}
              <button
                data-interactive="true"
                style={controlBtnStyle}
                onClick={(e) => handleControl('previous', e)}
                onMouseDown={(e) => e.stopPropagation()}
                title="Previous Track"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M6 6h2v12H6zm3.5 6l8.5 6V6z" />
                </svg>
              </button>
              <button
                data-interactive="true"
                style={playPauseBtnStyle}
                onClick={(e) => handleControl('togglePlayPause', e)}
                onMouseDown={(e) => e.stopPropagation()}
                title={isPlaying && !isPaused ? 'Pause' : 'Play'}
              >
                {isPlaying && !isPaused ? (
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="#000000">
                    <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
                  </svg>
                ) : (
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="#000000">
                    <path d="M8 5v14l11-7z" />
                  </svg>
                )}
              </button>
              <button
                data-interactive="true"
                style={controlBtnStyle}
                onClick={(e) => handleControl('next', e)}
                onMouseDown={(e) => e.stopPropagation()}
                title="Next Track"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z" />
                </svg>
              </button>
              {renderLikeBtn({ width: '28px', height: '28px' }, 14)}
            </div>
          </div>
        )}
      </div>

      {/* Right-Click Context Menu & Dismissal Overlay */}
      {contextMenu && (
        <React.Fragment>
          <div
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              width: '100vw',
              height: '100vh',
              zIndex: 9998,
              background: 'transparent',
            }}
            onClick={(e) => {
              e.stopPropagation();
              dispatch({ type: 'CLOSE_CONTEXT_MENU' });
            }}
            onContextMenu={(e) => {
              e.preventDefault();
              e.stopPropagation();
              dispatch({ type: 'CLOSE_CONTEXT_MENU' });
            }}
          />
          <div
            style={{
              position: 'fixed',
              top: `${contextMenu.y}px`,
              left: `${contextMenu.x}px`,
              zIndex: 9999,
              backgroundColor: 'rgba(24, 24, 28, 0.94)',
              backdropFilter: 'blur(30px) saturate(200%)',
              WebkitBackdropFilter: 'blur(30px) saturate(200%)',
              border: '1px solid rgba(255, 255, 255, 0.14)',
              borderRadius: '13px',
              padding: '5px',
              boxShadow: '0 12px 36px rgba(0, 0, 0, 0.65), 0 2px 8px rgba(0, 0, 0, 0.4)',
              minWidth: '135px',
              color: '#ffffff',
              userSelect: 'none',
              WebkitUserSelect: 'none',
            }}
            onClick={(e) => e.stopPropagation()}
            onContextMenu={(e) => e.preventDefault()}
          >
            <div
              style={{
                fontSize: '9.5px',
                fontWeight: '700',
                color: 'rgba(255, 255, 255, 0.45)',
                textTransform: 'uppercase',
                letterSpacing: '0.6px',
                padding: '4px 8px 5px 8px',
                borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
                marginBottom: '4px',
              }}
            >
              Widget Size
            </div>
            {[
              { id: 'small', label: 'Small' },
              { id: 'medium', label: 'Medium' },
              { id: 'large', label: 'Large' },
            ].map((item) => {
              const isSelected = (sizePreset || 'medium') === item.id;
              return (
                <div
                  key={item.id}
                  className="nowplaying-ctx-item"
                  onClick={(e) => {
                    e.stopPropagation();
                    dispatch({ type: 'SET_SIZE_PRESET', preset: item.id });
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '6px 10px',
                    borderRadius: '7px',
                    fontSize: '12px',
                    fontWeight: isSelected ? '600' : '400',
                    color: isSelected ? '#FFFFFF' : 'rgba(255, 255, 255, 0.82)',
                    backgroundColor: isSelected ? 'rgba(255, 255, 255, 0.12)' : 'transparent',
                    cursor: 'pointer',
                    margin: '1px 0',
                  }}
                >
                  <span>{item.label}</span>
                  {isSelected && (
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  )}
                </div>
              );
            })}
          </div>
        </React.Fragment>
      )}
    </React.Fragment>
  );
};

export const className = `
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color: #ffffff;

  button {
    transition: transform 0.08s ease, filter 0.12s ease !important;
  }
  button:hover {
    filter: brightness(1.2) !important;
  }
  button:active {
    transform: scale(0.88) !important;
  }

  .nowplaying-ctx-item {
    transition: background-color 0.1s ease, color 0.1s ease;
  }
  .nowplaying-ctx-item:hover {
    background-color: rgba(255, 255, 255, 0.18) !important;
    color: #ffffff !important;
  }
  .nowplaying-ctx-item:active {
    background-color: rgba(255, 255, 255, 0.25) !important;
  }
`;

// Styles - Medium (Standard)
const cardStyle = {
  position: 'relative',
  display: 'flex',
  flexDirection: 'column',
  gap: '10px',
  backgroundColor: 'rgba(24, 24, 28, 0.85)',
  backdropFilter: 'blur(30px) saturate(190%)',
  WebkitBackdropFilter: 'blur(30px) saturate(190%)',
  padding: '14px 16px',
  borderRadius: '20px',
  boxShadow: '0 16px 40px rgba(0, 0, 0, 0.55), 0 2px 6px rgba(0, 0, 0, 0.3)',
  border: '1px solid rgba(255, 255, 255, 0.12)',
  width: '300px',
  boxSizing: 'border-box',
};

// Styles - Small (1:1 Ratio, 154x154)
const smallCardStyle = {
  position: 'relative',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'space-between',
  width: '154px',
  height: '154px',
  padding: '12px 10px 10px 10px',
  borderRadius: '22px',
  backgroundColor: 'rgba(24, 24, 28, 0.88)',
  backdropFilter: 'blur(30px) saturate(190%)',
  WebkitBackdropFilter: 'blur(30px) saturate(190%)',
  boxShadow: '0 16px 40px rgba(0, 0, 0, 0.55), 0 2px 6px rgba(0, 0, 0, 0.3)',
  border: '1px solid rgba(255, 255, 255, 0.12)',
  boxSizing: 'border-box',
  overflow: 'hidden',
};

const smallArtworkContainerStyle = {
  position: 'relative',
  width: '56px',
  height: '56px',
  borderRadius: '12px',
  overflow: 'hidden',
  flexShrink: 0,
  boxShadow: '0 4px 12px rgba(0, 0, 0, 0.45)',
  backgroundColor: 'rgba(255, 255, 255, 0.05)',
  border: '1px solid rgba(255, 255, 255, 0.08)',
};

const smallControlBtnStyle = {
  background: 'rgba(255, 255, 255, 0.08)',
  border: '1px solid rgba(255, 255, 255, 0.1)',
  color: 'rgba(255, 255, 255, 0.85)',
  width: '24px',
  height: '24px',
  borderRadius: '50%',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  cursor: 'pointer',
  outline: 'none',
  padding: 0,
  transition: 'background 0.15s ease, transform 0.1s ease',
};

const smallPlayPauseBtnStyle = {
  background: '#FFFFFF',
  border: 'none',
  color: '#000000',
  width: '28px',
  height: '28px',
  borderRadius: '50%',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  cursor: 'pointer',
  outline: 'none',
  padding: 0,
  boxShadow: '0 2px 8px rgba(0, 0, 0, 0.35)',
  transition: 'transform 0.1s ease, filter 0.15s ease',
};

// Styles - Large (Expanded Cover Art)
const largeCardStyle = {
  position: 'relative',
  display: 'flex',
  flexDirection: 'column',
  gap: '12px',
  backgroundColor: 'rgba(24, 24, 28, 0.88)',
  backdropFilter: 'blur(30px) saturate(190%)',
  WebkitBackdropFilter: 'blur(30px) saturate(190%)',
  padding: '16px',
  borderRadius: '24px',
  boxShadow: '0 20px 48px rgba(0, 0, 0, 0.6), 0 2px 6px rgba(0, 0, 0, 0.35)',
  border: '1px solid rgba(255, 255, 255, 0.12)',
  width: '300px',
  boxSizing: 'border-box',
};

const largeArtworkContainerStyle = {
  position: 'relative',
  width: '268px',
  height: '268px',
  borderRadius: '16px',
  overflow: 'hidden',
  flexShrink: 0,
  boxShadow: '0 8px 24px rgba(0, 0, 0, 0.45)',
  backgroundColor: 'rgba(255, 255, 255, 0.05)',
  border: '1px solid rgba(255, 255, 255, 0.08)',
};

const topRowStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
};

const artworkContainerStyle = {
  position: 'relative',
  width: '52px',
  height: '52px',
  borderRadius: '12px',
  overflow: 'hidden',
  flexShrink: 0,
  boxShadow: '0 4px 12px rgba(0, 0, 0, 0.45)',
  backgroundColor: 'rgba(255, 255, 255, 0.05)',
  border: '1px solid rgba(255, 255, 255, 0.08)',
};

const artworkImageStyle = {
  width: '100%',
  height: '100%',
  objectFit: 'cover',
  display: 'block',
};

const artworkFallbackStyle = {
  width: '100%',
  height: '100%',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  backgroundColor: 'rgba(255, 255, 255, 0.06)',
};

const metaContainerStyle = {
  display: 'flex',
  flexDirection: 'column',
  justifyContent: 'center',
  flex: 1,
  minWidth: 0,
  overflow: 'hidden',
};

const titleStyle = {
  fontSize: '14px',
  fontWeight: '600',
  color: '#FFFFFF',
  whiteSpace: 'nowrap',
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  letterSpacing: '-0.2px',
  lineHeight: '1.25',
};

const artistStyle = {
  fontSize: '12px',
  fontWeight: '500',
  color: 'rgba(255, 255, 255, 0.72)',
  whiteSpace: 'nowrap',
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  marginTop: '2px',
};

const albumStyle = {
  fontSize: '11px',
  color: 'rgba(255, 255, 255, 0.42)',
  whiteSpace: 'nowrap',
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  marginTop: '1px',
};

const progressSectionStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: '4px',
  padding: '0 2px',
};

const progressBarTrackStyle = {
  width: '100%',
  height: '4px',
  borderRadius: '2px',
  backgroundColor: 'rgba(255, 255, 255, 0.15)',
  overflow: 'hidden',
};

const progressBarFillStyle = {
  height: '100%',
  backgroundColor: 'rgba(255, 255, 255, 0.75)',
  borderRadius: '2px',
  transition: 'width 0.3s ease',
};

const progressTimesStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  fontSize: '10px',
  color: 'rgba(255, 255, 255, 0.45)',
  fontWeight: '500',
  fontVariantNumeric: 'tabular-nums',
};

const controlsRowStyle = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: '16px',
  marginTop: '2px',
};

const controlBtnStyle = {
  background: 'rgba(255, 255, 255, 0.08)',
  border: '1px solid rgba(255, 255, 255, 0.1)',
  color: 'rgba(255, 255, 255, 0.85)',
  width: '30px',
  height: '30px',
  borderRadius: '50%',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  cursor: 'pointer',
  outline: 'none',
  padding: 0,
  transition: 'background 0.15s ease, transform 0.1s ease',
};

const playPauseBtnStyle = {
  background: '#FFFFFF',
  border: 'none',
  color: '#000000',
  width: '34px',
  height: '34px',
  borderRadius: '50%',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  cursor: 'pointer',
  outline: 'none',
  padding: 0,
  boxShadow: '0 3px 10px rgba(0, 0, 0, 0.35)',
  transition: 'transform 0.1s ease, filter 0.15s ease',
};
