import { React, run } from 'uebersicht';

export const refreshFrequency = 1500;

export const command = `python3 "$HOME/Library/Application Support/Übersicht/widgets/nowplaying.widget/get_song.py" 2>/dev/null || python3 "nowplaying.widget/get_song.py" 2>/dev/null || python3 "ytmusic.widget/get_song.py"`;

const STORAGE_KEY = 'nowplaying_widget_position';
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

const initialPos = getInitialPosition();

export const initialState = {
  x: initialPos.x,
  y: initialPos.y,
  isDragging: false,
  dragStartX: 0,
  dragStartY: 0,
  startPosX: 0,
  startPosY: 0,
  cardWidth: 320,
  cardHeight: 160,
  data: { playing: false },
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
      return {
        ...previousState,
        data: parsed,
        error: null,
      };
    } catch (err) {
      return {
        ...previousState,
        error: err.message,
      };
    }
  }

  if (event.type === 'OPTIMISTIC_TOGGLE_PLAY') {
    if (!previousState.data || !previousState.data.playing) return previousState;
    const currentRate = previousState.data.rate ?? 1;
    const nextRate = currentRate === 1 ? 0 : 1;
    return {
      ...previousState,
      data: {
        ...previousState.data,
        rate: nextRate,
      },
    };
  }

  if (event.type === 'START_DRAG') {
    return {
      ...previousState,
      isDragging: true,
      dragStartX: event.clientX,
      dragStartY: event.clientY,
      startPosX: previousState.x,
      startPosY: previousState.y,
      cardWidth: event.cardWidth || previousState.cardWidth || 320,
      cardHeight: event.cardHeight || previousState.cardHeight || 160,
    };
  }

  if (event.type === 'MOVE_DRAG' && previousState.isDragging) {
    const deltaX = event.clientX - previousState.dragStartX;
    const deltaY = event.clientY - previousState.dragStartY;
    const cardWidth = previousState.cardWidth || 320;
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

  return previousState;
};

const formatTime = (secs) => {
  if (!secs || isNaN(secs) || secs < 0) return '0:00';
  const m = Math.floor(secs / 60);
  const s = Math.floor(secs % 60);
  return `${m}:${s < 10 ? '0' : ''}${s}`;
};

export const render = (state, dispatch) => {
  const { data, error, x = 50, y = 50, isDragging } = state || {};

  const handleMouseDown = (e) => {
    if (e.button !== 0) return;
    if (e.target.closest('button') || e.target.closest('[data-interactive="true"]')) return;

    e.preventDefault();
    const rect = e.currentTarget ? e.currentTarget.getBoundingClientRect() : null;
    const cardWidth = rect ? rect.width : 320;
    const cardHeight = rect ? rect.height : 160;

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

  const handleControl = (action, e) => {
    e.stopPropagation();
    if (action === 'togglePlayPause') {
      dispatch({ type: 'OPTIMISTIC_TOGGLE_PLAY' });
    }
    const cli = '/opt/homebrew/bin/nowplaying-cli';
    run(`${cli} ${action} 2>/dev/null || nowplaying-cli ${action}`);
  };

  const isPlaying = data && data.playing && data.title;
  const isPaused = isPlaying && data.rate === 0;

  const duration = data?.duration || 0;
  const elapsed = data?.elapsed || 0;
  const progressPercent = duration > 0 ? Math.min(100, Math.max(0, (elapsed / duration) * 100)) : 0;

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

  // State: Nothing Playing or Error
  if (error || !isPlaying) {
    return (
      <div style={positionStyle} onMouseDown={handleMouseDown}>
        <div style={emptyCardStyle}>
          <div style={emptyIconStyle}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.7)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 18V5l12-2v13" />
              <circle cx="6" cy="18" r="3" />
              <circle cx="18" cy="16" r="3" />
            </svg>
          </div>
          <div style={emptyTextGroupStyle}>
            <div style={emptyTitleStyle}>{error ? 'Widget Error' : 'Nothing Playing'}</div>
            {error && <div style={emptySubtitleStyle}>{error}</div>}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={positionStyle} onMouseDown={handleMouseDown}>
      <div style={cardStyle}>
        {/* Top Section: Artwork + Info */}
        <div style={topRowStyle}>
          {/* Artwork Thumbnail */}
          <div style={artworkContainerStyle}>
            {data.artwork ? (
              <img src={data.artwork} alt="Album Art" style={artworkImageStyle} />
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
          <div style={metaContainerStyle}>
            <div style={titleStyle} title={data.title}>
              {data.title}
            </div>

            <div style={artistStyle} title={data.artist || 'Unknown Artist'}>
              {data.artist || 'Unknown Artist'}
            </div>

            {data.album && data.album !== data.title && (
              <div style={albumStyle} title={data.album}>
                {data.album}
              </div>
            )}
          </div>
        </div>

        {/* Middle Section: Progress Bar */}
        {duration > 0 && (
          <div style={progressSectionStyle}>
            <div style={progressBarTrackStyle}>
              <div
                style={{
                  ...progressBarFillStyle,
                  width: `${progressPercent}%`,
                }}
              />
            </div>
            <div style={progressTimesStyle}>
              <span>{formatTime(elapsed)}</span>
              <span>{formatTime(duration)}</span>
            </div>
          </div>
        )}

        {/* Bottom Section: Media Controls */}
        <div style={controlsRowStyle}>
          {/* Previous Button */}
          <button
            data-interactive="true"
            style={controlBtnStyle}
            onClick={(e) => handleControl('previous', e)}
            onMouseDown={(e) => e.stopPropagation()}
            title="Previous Track"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <path d="M6 6h2v12H6zm3.5 6l8.5 6V6z" />
            </svg>
          </button>

          {/* Play / Pause Toggle Button */}
          <button
            data-interactive="true"
            style={playPauseBtnStyle}
            onClick={(e) => handleControl('togglePlayPause', e)}
            onMouseDown={(e) => e.stopPropagation()}
            title={isPaused ? 'Play' : 'Pause'}
          >
            {isPaused ? (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="#000000">
                <path d="M8 5v14l11-7z" />
              </svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="#000000">
                <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
              </svg>
            )}
          </button>

          {/* Next Button */}
          <button
            data-interactive="true"
            style={controlBtnStyle}
            onClick={(e) => handleControl('next', e)}
            onMouseDown={(e) => e.stopPropagation()}
            title="Next Track"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <path d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z" />
            </svg>
          </button>
        </div>
      </div>
    </div>
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
`;

// Styles
const cardStyle = {
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
  minWidth: '270px',
  maxWidth: '320px',
  boxSizing: 'border-box',
};

const emptyCardStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
  backgroundColor: 'rgba(22, 22, 26, 0.82)',
  backdropFilter: 'blur(25px)',
  WebkitBackdropFilter: 'blur(25px)',
  padding: '10px 16px',
  borderRadius: '16px',
  boxShadow: '0 12px 30px rgba(0, 0, 0, 0.45)',
  border: '1px solid rgba(255, 255, 255, 0.1)',
  maxWidth: '260px',
};

const emptyIconStyle = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  flexShrink: 0,
  width: '30px',
  height: '30px',
  borderRadius: '8px',
  backgroundColor: 'rgba(255, 255, 255, 0.08)',
};

const emptyTextGroupStyle = {
  display: 'flex',
  flexDirection: 'column',
  overflow: 'hidden',
};

const emptyTitleStyle = {
  fontSize: '13px',
  fontWeight: '600',
  color: 'rgba(255, 255, 255, 0.95)',
  letterSpacing: '-0.2px',
};

const emptySubtitleStyle = {
  fontSize: '11px',
  color: 'rgba(255, 255, 255, 0.5)',
  marginTop: '2px',
  whiteSpace: 'nowrap',
  overflow: 'hidden',
  textOverflow: 'ellipsis',
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
