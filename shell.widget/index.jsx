import { React, run } from 'uebersicht';

export const refreshFrequency = false;

export const command = '';

const POS_KEY = 'shell_widget_position';
const SIZE_KEY = 'shell_widget_size';
const SCREEN_MARGIN = 2;

// Exact color palette extracted from user's iTerm2 profile
const ITERM2_THEME = {
  bg: 'rgba(28, 27, 25, 0.90)',
  cardBorder: 'rgba(255, 255, 255, 0.12)',
  fg: '#fce8c3',
  cursor: '#fbb829',
  selection: '#fce8c3',
  black: '#1c1b19',
  red: '#ef2f27',
  green: '#519f50',
  yellow: '#fbb829',
  blue: '#2c78bf',
  magenta: '#e02c6d',
  cyan: '#0aaeb3',
  white: '#baa67f',
  brightBlack: '#918175',
  brightRed: '#f75341',
  brightGreen: '#98bc37',
  brightYellow: '#fed06e',
  brightBlue: '#68a8e4',
  brightMagenta: '#ff5c8f',
  brightCyan: '#2be4d0',
  brightWhite: '#fce8c3',
};

const FG_MAP = {
  '30': ITERM2_THEME.black,
  '31': ITERM2_THEME.red,
  '32': ITERM2_THEME.green,
  '33': ITERM2_THEME.yellow,
  '34': ITERM2_THEME.blue,
  '35': ITERM2_THEME.magenta,
  '36': ITERM2_THEME.cyan,
  '37': ITERM2_THEME.white,
  '39': ITERM2_THEME.fg,
  '90': ITERM2_THEME.brightBlack,
  '91': ITERM2_THEME.brightRed,
  '92': ITERM2_THEME.brightGreen,
  '93': ITERM2_THEME.brightYellow,
  '94': ITERM2_THEME.brightBlue,
  '95': ITERM2_THEME.brightMagenta,
  '96': ITERM2_THEME.brightCyan,
  '97': ITERM2_THEME.brightWhite,
};

const BG_MAP = {
  '40': ITERM2_THEME.black,
  '41': ITERM2_THEME.red,
  '42': ITERM2_THEME.green,
  '43': ITERM2_THEME.yellow,
  '44': ITERM2_THEME.blue,
  '45': ITERM2_THEME.magenta,
  '46': ITERM2_THEME.cyan,
  '47': ITERM2_THEME.white,
  '49': 'transparent',
  '100': ITERM2_THEME.brightBlack,
  '101': ITERM2_THEME.brightRed,
  '102': ITERM2_THEME.brightGreen,
  '103': ITERM2_THEME.brightYellow,
  '104': ITERM2_THEME.brightBlue,
  '105': ITERM2_THEME.brightMagenta,
  '106': ITERM2_THEME.brightCyan,
  '107': ITERM2_THEME.brightWhite,
};

const getInitialPosition = () => {
  try {
    const saved = localStorage.getItem(POS_KEY);
    if (saved) {
      const parsed = JSON.parse(saved);
      if (typeof parsed.x === 'number' && typeof parsed.y === 'number') {
        const maxX = Math.max(SCREEN_MARGIN, (window.innerWidth || 1920) - 400);
        const maxY = Math.max(SCREEN_MARGIN, (window.innerHeight || 1080) - 240);
        return {
          x: Math.max(SCREEN_MARGIN, Math.min(maxX, parsed.x)),
          y: Math.max(SCREEN_MARGIN, Math.min(maxY, parsed.y)),
        };
      }
    }
  } catch (e) {}
  return { x: 50, y: 220 };
};

const getInitialSize = () => {
  try {
    const saved = localStorage.getItem(SIZE_KEY);
    if (saved) {
      const parsed = JSON.parse(saved);
      if (typeof parsed.w === 'number' && typeof parsed.h === 'number') {
        return {
          w: Math.max(220, Math.min((window.innerWidth || 1920) - 20, parsed.w)),
          h: Math.max(120, Math.min((window.innerHeight || 1080) - 20, parsed.h)),
        };
      }
    }
  } catch (e) {}
  return { w: 420, h: 220 };
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
  lines: [],
  inputValue: '',
  history: [],
  historyIndex: -1,
};

export const updateState = (event, previousState) => {
  if (!previousState) return initialState;

  if (event.type === 'UB/COMMAND_RAN') {
    if (event.error) {
      return {
        ...previousState,
        lines: [...previousState.lines, { type: 'error', text: event.error }],
      };
    }
    if (event.output && event.output.trim()) {
      return {
        ...previousState,
        lines: [...previousState.lines, { type: 'output', text: event.output }],
      };
    }
    return previousState;
  }

  if (event.type === 'ADD_LINE') {
    return {
      ...previousState,
      lines: [...previousState.lines, { type: event.lineType, text: event.text }],
    };
  }

  if (event.type === 'CLEAR_LINES') {
    return {
      ...previousState,
      lines: [],
    };
  }

  if (event.type === 'SET_INPUT') {
    return {
      ...previousState,
      inputValue: event.value,
      historyIndex: event.historyIndex !== undefined ? event.historyIndex : previousState.historyIndex,
    };
  }

  if (event.type === 'PUSH_HISTORY') {
    return {
      ...previousState,
      history: [...previousState.history, event.cmd],
      historyIndex: -1,
      inputValue: '',
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

    const maxW = Math.max(220, window.innerWidth - previousState.x - SCREEN_MARGIN);
    const maxH = Math.max(120, window.innerHeight - previousState.y - SCREEN_MARGIN);

    const newW = Math.max(220, Math.min(maxW, previousState.startW + deltaW));
    const newH = Math.max(120, Math.min(maxH, previousState.startH + deltaH));

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

// ANSI color parser for rich terminal rendering
function renderAnsiText(raw) {
  if (!raw) return null;

  // Clean OSC escape sequences and cursor motion
  const cleaned = raw
    .replace(/\x1b\][^\x07\x1b]*(\x07|\x1b\\)/g, '')
    .replace(/\x1b\[[0-9;]*[A-HJKSTf-n]/g, '')
    .replace(/\x1b\[\?[0-9;]*[a-zA-Z]/g, '');

  const regex = /\x1b\[([0-9;]*)m/g;
  let lastIndex = 0;
  const elements = [];
  let currentFg = ITERM2_THEME.fg;
  let currentBg = 'transparent';
  let isBold = false;
  let isDim = false;
  let match;

  while ((match = regex.exec(cleaned)) !== null) {
    const textChunk = cleaned.slice(lastIndex, match.index);
    if (textChunk) {
      elements.push(
        <span
          key={elements.length}
          style={{
            color: currentFg,
            backgroundColor: currentBg,
            fontWeight: isBold ? '700' : '400',
            opacity: isDim ? 0.6 : 1,
          }}
        >
          {textChunk}
        </span>
      );
    }

    const codes = match[1] ? match[1].split(';') : ['0'];
    for (const code of codes) {
      if (code === '0' || code === '') {
        currentFg = ITERM2_THEME.fg;
        currentBg = 'transparent';
        isBold = false;
        isDim = false;
      } else if (code === '1') {
        isBold = true;
      } else if (code === '2') {
        isDim = true;
      } else if (code === '22') {
        isBold = false;
        isDim = false;
      } else if (FG_MAP[code]) {
        currentFg = FG_MAP[code];
      } else if (BG_MAP[code]) {
        currentBg = BG_MAP[code];
      }
    }

    lastIndex = regex.lastIndex;
  }

  const remaining = cleaned.slice(lastIndex);
  if (remaining) {
    elements.push(
      <span
        key={elements.length}
        style={{
          color: currentFg,
          backgroundColor: currentBg,
          fontWeight: isBold ? '700' : '400',
          opacity: isDim ? 0.6 : 1,
        }}
      >
        {remaining}
      </span>
    );
  }

  return elements;
}

export const render = (state, dispatch) => {
  const {
    x = 50,
    y = 220,
    w = 420,
    h = 220,
    isDragging,
    isResizing,
    lines = [],
    inputValue = '',
    history = [],
    historyIndex = -1,
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

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      const cmd = inputValue.trim();
      if (!cmd) return;

      if (cmd.toLowerCase() === 'clear') {
        dispatch({ type: 'CLEAR_LINES' });
        dispatch({ type: 'PUSH_HISTORY', cmd });
        return;
      }

      // Add command line
      dispatch({ type: 'ADD_LINE', lineType: 'command', text: cmd });
      dispatch({ type: 'PUSH_HISTORY', cmd });

      // Run natively in zsh with complete PATH
      const fullCmd = `export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"; zsh -l -c ${JSON.stringify(cmd)}`;

      run(fullCmd)
        .then((output) => {
          if (output && output.trim()) {
            dispatch({ type: 'ADD_LINE', lineType: 'output', text: output });
          }
        })
        .catch((err) => {
          const errMsg = err?.message || String(err);
          dispatch({ type: 'ADD_LINE', lineType: 'error', text: errMsg });
        });
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (history.length > 0) {
        const nextIdx = historyIndex === -1 ? history.length - 1 : Math.max(0, historyIndex - 1);
        dispatch({ type: 'SET_INPUT', value: history[nextIdx], historyIndex: nextIdx });
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIndex !== -1) {
        const nextIdx = historyIndex + 1;
        if (nextIdx >= history.length) {
          dispatch({ type: 'SET_INPUT', value: '', historyIndex: -1 });
        } else {
          dispatch({ type: 'SET_INPUT', value: history[nextIdx], historyIndex: nextIdx });
        }
      }
    }
  };

  const positionStyle = {
    position: 'absolute',
    top: `${y}px`,
    left: `${x}px`,
    width: `${w}px`,
    height: `${h}px`,
    zIndex: 998,
    cursor: isDragging ? 'grabbing' : isResizing ? 'se-resize' : 'grab',
    userSelect: 'none',
    WebkitUserSelect: 'none',
    boxSizing: 'border-box',
  };

  return (
    <div style={positionStyle} onMouseDown={handleMouseDown}>
      <div style={windowStyle}>
        {/* Title Bar */}
        <div style={titleBarStyle}>
          <div style={trafficLightsStyle}>
            <span
              style={{ ...dotStyle, backgroundColor: '#ff5f56' }}
              onClick={(e) => {
                e.stopPropagation();
                dispatch({ type: 'CLEAR_LINES' });
              }}
              title="Clear terminal"
              data-no-drag="true"
            />
            <span style={{ ...dotStyle, backgroundColor: '#ffbd2e' }} />
            <span style={{ ...dotStyle, backgroundColor: '#27c93f' }} />
          </div>
          <div style={titleTextStyle}>zsh</div>
          <div style={{ width: '48px' }} />
        </div>

        {/* Terminal Body */}
        <div style={terminalBodyStyle} data-no-drag="true">
          {lines.map((line, idx) => (
            <div key={idx} style={lineStyle}>
              {line.type === 'command' ? (
                <span>
                  <span style={{ color: ITERM2_THEME.yellow, marginRight: '6px' }}>❯</span>
                  <span style={{ color: ITERM2_THEME.brightWhite }}>{line.text}</span>
                </span>
              ) : line.type === 'error' ? (
                <span style={{ color: ITERM2_THEME.red }}>{line.text}</span>
              ) : (
                <pre style={preStyle}>{renderAnsiText(line.text)}</pre>
              )}
            </div>
          ))}

          {/* Interactive Input Prompt */}
          <div style={promptRowStyle}>
            <span style={promptSymbolStyle}>❯</span>
            <input
              type="text"
              value={inputValue}
              onChange={(e) => dispatch({ type: 'SET_INPUT', value: e.target.value })}
              onKeyDown={handleKeyDown}
              placeholder="run command..."
              style={inputStyle}
              data-no-drag="true"
              autoFocus={false}
            />
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
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, sans-serif;
  color: ${ITERM2_THEME.fg};

  input::placeholder {
    color: rgba(252, 232, 195, 0.35);
  }
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
  cursor: 'pointer',
};

const titleTextStyle = {
  fontSize: '11px',
  fontWeight: '600',
  color: 'rgba(252, 232, 195, 0.65)',
  letterSpacing: '0.2px',
};

const terminalBodyStyle = {
  flex: 1,
  padding: '10px 14px',
  overflowY: 'auto',
  overflowX: 'hidden',
  fontFamily: '"SF Mono", "JetBrains Mono", Menlo, Monaco, Consolas, monospace',
  fontSize: '12px',
  lineHeight: '1.45',
  cursor: 'text',
  userSelect: 'text',
  WebkitUserSelect: 'text',
};

const lineStyle = {
  marginBottom: '4px',
  wordBreak: 'break-word',
  whiteSpace: 'pre-wrap',
};

const preStyle = {
  margin: 0,
  fontFamily: 'inherit',
  fontSize: 'inherit',
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-word',
};

const promptRowStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '6px',
  marginTop: '6px',
};

const promptSymbolStyle = {
  color: ITERM2_THEME.yellow,
  fontWeight: '700',
  fontSize: '12px',
};

const inputStyle = {
  flex: 1,
  background: 'transparent',
  border: 'none',
  outline: 'none',
  fontFamily: 'inherit',
  fontSize: '12px',
  color: ITERM2_THEME.fg,
  padding: 0,
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
