import { React } from 'uebersicht';

export const refreshFrequency = 60; // Poll bridge every 60ms (~16 FPS)

export const command = `python3 "$HOME/Library/Application Support/Übersicht/widgets/cava.widget/cava_bridge.py" 2>/dev/null || python3 "cava.widget/cava_bridge.py" 2>/dev/null`;

const POS_KEY = 'cava_widget_position';
const SIZE_KEY = 'cava_widget_size';
const SCREEN_MARGIN = 2;
const DEFAULT_BARS_COUNT = 28;

// Exact color palette extracted from user's iTerm2 profile and ~/.config/cava/config
const ITERM2_THEME = {
  bg: 'rgba(28, 27, 25, 0.90)',
  cardBorder: 'rgba(255, 255, 255, 0.12)',
  fg: '#fce8c3',
  title: 'rgba(252, 232, 195, 0.70)',
  subtitle: 'rgba(252, 232, 195, 0.40)',
  // Vertical gradient matching ~/.config/cava/config gradient
  gradBase: '#59cc33',
  gradMid: '#cccc33',
  gradPeak: '#cc3333',
};

const getInitialPosition = () => {
  try {
    const saved = localStorage.getItem(POS_KEY);
    if (saved) {
      const parsed = JSON.parse(saved);
      if (typeof parsed.x === 'number' && typeof parsed.y === 'number') {
        const maxX = Math.max(SCREEN_MARGIN, (window.innerWidth || 1920) - 380);
        const maxY = Math.max(SCREEN_MARGIN, (window.innerHeight || 1080) - 160);
        return {
          x: Math.max(SCREEN_MARGIN, Math.min(maxX, parsed.x)),
          y: Math.max(SCREEN_MARGIN, Math.min(maxY, parsed.y)),
        };
      }
    }
  } catch (e) {}
  return { x: 50, y: 380 };
};

const getInitialSize = () => {
  try {
    const saved = localStorage.getItem(SIZE_KEY);
    if (saved) {
      const parsed = JSON.parse(saved);
      if (typeof parsed.w === 'number' && typeof parsed.h === 'number') {
        return {
          w: Math.max(200, Math.min((window.innerWidth || 1920) - 20, parsed.w)),
          h: Math.max(90, Math.min((window.innerHeight || 1080) - 20, parsed.h)),
        };
      }
    }
  } catch (e) {}
  return { w: 380, h: 160 };
};

const initialPos = getInitialPosition();
const initialSize = getInitialSize();

export const initialState = {
  x: initialPos.x,
  y: initialPos.y,
  w: initialSize.w,
  h: initialSize.h,
  isDragging: false,
  isResizing: false,
  dragStartX: 0,
  dragStartY: 0,
  startPosX: 0,
  startPosY: 0,
  resizeStartX: 0,
  resizeStartY: 0,
  startW: 0,
  startH: 0,
  bars: new Array(DEFAULT_BARS_COUNT).fill(0),
};

export const updateState = (event, previousState) => {
  if (!previousState) return initialState;

  // Handle stdout from cava_bridge.py
  if (event.output && typeof event.output === 'string') {
    const parts = event.output.trim().split(';').filter(Boolean);
    if (parts.length > 0) {
      const parsedBars = parts.map((val) => {
        const num = parseInt(val, 10);
        return isNaN(num) ? 0 : Math.max(0, Math.min(100, num));
      });
      return {
        ...previousState,
        bars: parsedBars,
      };
    }
  }

  if (event.type === 'START_DRAG') {
    return {
      ...previousState,
      isDragging: true,
      dragStartX: event.clientX,
      dragStartY: event.clientY,
      startPosX: previousState.x,
      startPosY: previousState.y,
    };
  }

  if (event.type === 'MOVE_DRAG' && previousState.isDragging) {
    const deltaX = event.clientX - previousState.dragStartX;
    const deltaY = event.clientY - previousState.dragStartY;
    const maxX = Math.max(SCREEN_MARGIN, window.innerWidth - previousState.w - SCREEN_MARGIN);
    const maxY = Math.max(SCREEN_MARGIN, window.innerHeight - previousState.h - SCREEN_MARGIN);

    const newX = Math.max(SCREEN_MARGIN, Math.min(maxX, previousState.startPosX + deltaX));
    const newY = Math.max(SCREEN_MARGIN, Math.min(maxY, previousState.startPosY + deltaY));

    try {
      localStorage.setItem(POS_KEY, JSON.stringify({ x: newX, y: newY }));
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

  if (event.type === 'START_RESIZE') {
    return {
      ...previousState,
      isResizing: true,
      resizeStartX: event.clientX,
      resizeStartY: event.clientY,
      startW: previousState.w,
      startH: previousState.h,
    };
  }

  if (event.type === 'MOVE_RESIZE' && previousState.isResizing) {
    const deltaW = event.clientX - previousState.resizeStartX;
    const deltaH = event.clientY - previousState.resizeStartY;

    const maxW = Math.max(200, window.innerWidth - previousState.x - SCREEN_MARGIN);
    const maxH = Math.max(90, window.innerHeight - previousState.y - SCREEN_MARGIN);

    const newW = Math.max(200, Math.min(maxW, previousState.startW + deltaW));
    const newH = Math.max(90, Math.min(maxH, previousState.startH + deltaH));

    try {
      localStorage.setItem(SIZE_KEY, JSON.stringify({ w: newW, h: newH }));
    } catch (e) {}

    return {
      ...previousState,
      w: newW,
      h: newH,
    };
  }

  if (event.type === 'END_RESIZE') {
    return {
      ...previousState,
      isResizing: false,
    };
  }

  return previousState;
};

export const render = (state, dispatch) => {
  const {
    x = 50,
    y = 380,
    w = 380,
    h = 160,
    isDragging,
    isResizing,
    bars = [],
  } = state || {};

  const handleMouseDown = (e) => {
    if (e.button !== 0) return;
    if (e.target.closest('[data-no-drag="true"]')) return;

    e.preventDefault();
    dispatch({ type: 'START_DRAG', clientX: e.clientX, clientY: e.clientY });

    const onMouseMove = (moveEvent) => {
      dispatch({ type: 'MOVE_DRAG', clientX: moveEvent.clientX, clientY: moveEvent.clientY });
    };

    const onMouseUp = () => {
      dispatch({ type: 'END_DRAG' });
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
    };

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
  };

  const handleResizeStart = (e) => {
    if (e.button !== 0) return;
    e.preventDefault();
    e.stopPropagation();

    dispatch({ type: 'START_RESIZE', clientX: e.clientX, clientY: e.clientY });

    const onMouseMove = (moveEvent) => {
      dispatch({ type: 'MOVE_RESIZE', clientX: moveEvent.clientX, clientY: moveEvent.clientY });
    };

    const onMouseUp = () => {
      dispatch({ type: 'END_RESIZE' });
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
    };

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
  };

  const positionStyle = {
    position: 'absolute',
    top: `${y}px`,
    left: `${x}px`,
    width: `${w}px`,
    height: `${h}px`,
    zIndex: 997,
    cursor: isDragging ? 'grabbing' : isResizing ? 'se-resize' : 'grab',
    userSelect: 'none',
    WebkitUserSelect: 'none',
    boxSizing: 'border-box',
  };

  // Determine active display bars count based on current window width
  const barsData = bars.length > 0 ? bars : new Array(DEFAULT_BARS_COUNT).fill(0);

  return (
    <div style={positionStyle} onMouseDown={handleMouseDown}>
      <div style={windowStyle}>
        {/* Title Bar */}
        <div style={titleBarStyle}>
          <div style={trafficLightsStyle}>
            <span style={{ ...dotStyle, backgroundColor: '#ff5f56' }} />
            <span style={{ ...dotStyle, backgroundColor: '#ffbd2e' }} />
            <span style={{ ...dotStyle, backgroundColor: '#27c93f' }} />
          </div>
          <div style={titleTextStyle}>cava</div>
          <div style={statusLabelStyle}>tap</div>
        </div>

        {/* Terminal Visualizer Body */}
        <div style={terminalBodyStyle} data-no-drag="true">
          <div style={barsContainerStyle}>
            {barsData.map((val, idx) => {
              // Percentage height (min 2% so idle head remains visible as in cava)
              const heightPct = Math.max(2, val);
              return (
                <div key={idx} style={barColumnStyle}>
                  <div
                    style={{
                      ...barFillStyle,
                      height: `${heightPct}%`,
                    }}
                  />
                </div>
              );
            })}
          </div>
        </div>

        {/* Resize Handle */}
        <div
          data-no-drag="true"
          style={resizeHandleStyle}
          onMouseDown={handleResizeStart}
          title="Drag to resize"
        >
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
            <circle cx="8" cy="8" r="1" fill="rgba(255,255,255,0.35)" />
            <circle cx="8" cy="4" r="1" fill="rgba(255,255,255,0.35)" />
            <circle cx="4" cy="8" r="1" fill="rgba(255,255,255,0.35)" />
          </svg>
        </div>
      </div>
    </div>
  );
};

export const className = `
  font-family: -apple-system, BlinkMacSystemFont, "SF Mono", Menlo, Monaco, Consolas, monospace;
  color: ${ITERM2_THEME.fg};
`;

const windowStyle = {
  position: 'relative',
  width: '100%',
  height: '100%',
  backgroundColor: ITERM2_THEME.bg,
  backdropFilter: 'blur(28px) saturate(180%)',
  WebkitBackdropFilter: 'blur(28px) saturate(180%)',
  borderRadius: '16px',
  boxShadow: '0 16px 40px rgba(0, 0, 0, 0.55), 0 2px 6px rgba(0, 0, 0, 0.3)',
  border: `1px solid ${ITERM2_THEME.cardBorder}`,
  boxSizing: 'border-box',
  overflow: 'hidden',
  display: 'flex',
  flexDirection: 'column',
};

const titleBarStyle = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '8px 12px',
  borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
  backgroundColor: 'rgba(0, 0, 0, 0.15)',
  cursor: 'grab',
  flexShrink: 0,
};

const trafficLightsStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '6px',
  width: '48px',
};

const dotStyle = {
  width: '9px',
  height: '9px',
  borderRadius: '50%',
  display: 'inline-block',
};

const titleTextStyle = {
  fontSize: '11px',
  fontWeight: '600',
  color: ITERM2_THEME.title,
  letterSpacing: '0.2px',
};

const statusLabelStyle = {
  fontSize: '10px',
  color: ITERM2_THEME.subtitle,
  width: '48px',
  textAlign: 'right',
  fontFamily: '"SF Mono", Menlo, monospace',
};

const terminalBodyStyle = {
  flex: 1,
  padding: '12px 14px 10px',
  display: 'flex',
  flexDirection: 'column',
  justifyContent: 'flex-end',
  overflow: 'hidden',
  boxSizing: 'border-box',
};

const barsContainerStyle = {
  width: '100%',
  height: '100%',
  display: 'flex',
  alignItems: 'flex-end',
  justifyContent: 'space-between',
  gap: '3px',
};

const barColumnStyle = {
  flex: 1,
  height: '100%',
  display: 'flex',
  alignItems: 'flex-end',
  justifyContent: 'center',
  minWidth: '2px',
};

const barFillStyle = {
  width: '100%',
  // Terminal 8-stop gradient matching ~/.config/cava/config
  background: `linear-gradient(to top, 
    ${ITERM2_THEME.gradBase} 0%, 
    #80cc33 25%, 
    ${ITERM2_THEME.gradMid} 55%, 
    #cc8033 80%, 
    ${ITERM2_THEME.gradPeak} 100%
  )`,
  // Sharp terminal block corners with subtle notch segmentation
  borderRadius: '1px 1px 0 0',
  transition: 'height 0.055s ease-out',
  boxShadow: '0 0 6px rgba(89, 204, 51, 0.25)',
};

const resizeHandleStyle = {
  position: 'absolute',
  bottom: 0,
  right: 0,
  width: '18px',
  height: '18px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  cursor: 'se-resize',
  zIndex: 10,
};
