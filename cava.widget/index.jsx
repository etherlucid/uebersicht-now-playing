import { React } from 'uebersicht';

export const refreshFrequency = 10000;

export const command = `python3 "$HOME/Library/Application Support/Übersicht/widgets/cava.widget/cava_server.py" 2>/dev/null || python3 "cava.widget/cava_server.py" 2>/dev/null`;

const POS_STORAGE_KEY = 'cava_widget_position';
const SIZE_STORAGE_KEY = 'cava_widget_size';
const SCREEN_MARGIN = 2;
const CANVAS_ID = 'cava-visualizer-canvas';

const getInitialPosition = () => {
  try {
    const saved = localStorage.getItem(POS_STORAGE_KEY);
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
  return { x: 50, y: 220 };
};

const getInitialSize = () => {
  try {
    const saved = localStorage.getItem(SIZE_STORAGE_KEY);
    if (saved) {
      const parsed = JSON.parse(saved);
      if (typeof parsed.w === 'number' && typeof parsed.h === 'number') {
        return {
          w: Math.max(160, Math.min((window.innerWidth || 1920) - 20, parsed.w)),
          h: Math.max(60, Math.min((window.innerHeight || 1080) - 20, parsed.h)),
        };
      }
    }
  } catch (e) {}
  return { w: 320, h: 120 };
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
};

export const updateState = (event, previousState) => {
  if (!previousState) return initialState;

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
      localStorage.setItem(POS_STORAGE_KEY, JSON.stringify({ x: newX, y: newY }));
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

    const maxW = Math.max(160, window.innerWidth - previousState.x - SCREEN_MARGIN);
    const maxH = Math.max(60, window.innerHeight - previousState.y - SCREEN_MARGIN);

    const newW = Math.max(160, Math.min(maxW, previousState.startW + deltaW));
    const newH = Math.max(60, Math.min(maxH, previousState.startH + deltaH));

    try {
      localStorage.setItem(SIZE_STORAGE_KEY, JSON.stringify({ w: newW, h: newH }));
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

// Canvas visualizer loop
const initVisualizerLoop = () => {
  if (typeof window === 'undefined') return;

  if (!window.__cava_bars) {
    window.__cava_bars = new Array(32).fill(0);
  }

  // Connect to SSE stream if not connected
  if (!window.__cava_es || window.__cava_es.readyState === 2) {
    try {
      const es = new EventSource('http://127.0.0.1:41425/stream');
      es.onmessage = (e) => {
        const raw = e.data.trim().split(';').filter(Boolean).map(Number);
        if (raw.length > 0) {
          window.__cava_bars = raw;
        }
      };
      es.onerror = () => {
        // EventSource will automatically retry
      };
      window.__cava_es = es;
    } catch (err) {}
  }

  // Animation frame loop
  if (!window.__cava_raf_started) {
    window.__cava_raf_started = true;
    const smoothed = new Array(32).fill(0);

    const renderFrame = () => {
      const canvas = document.getElementById(CANVAS_ID);
      if (canvas) {
        const ctx = canvas.getContext('2d');
        const dpr = window.devicePixelRatio || 2;
        const w = canvas.clientWidth;
        const h = canvas.clientHeight;

        if (canvas.width !== Math.floor(w * dpr) || canvas.height !== Math.floor(h * dpr)) {
          canvas.width = Math.floor(w * dpr);
          canvas.height = Math.floor(h * dpr);
        }

        ctx.save();
        ctx.scale(dpr, dpr);
        ctx.clearRect(0, 0, w, h);

        const bars = window.__cava_bars || [];
        const count = bars.length || 32;
        const gap = Math.max(2, Math.floor(w / (count * 4)));
        const totalGap = (count - 1) * gap;
        const barWidth = Math.max(2, (w - totalGap) / count);

        // Gradient matching the glassmorphic theme
        const grad = ctx.createLinearGradient(0, h, 0, 0);
        grad.addColorStop(0, 'rgba(255, 255, 255, 0.25)');
        grad.addColorStop(0.6, 'rgba(255, 255, 255, 0.65)');
        grad.addColorStop(1, 'rgba(255, 255, 255, 0.95)');

        ctx.fillStyle = grad;

        for (let i = 0; i < count; i++) {
          const target = (bars[i] || 0) / 100;
          smoothed[i] = (smoothed[i] || 0) * 0.65 + target * 0.35;
          const barH = Math.max(3, smoothed[i] * (h - 2));
          const xPos = i * (barWidth + gap);
          const yPos = h - barH;

          // Render bar with rounded top
          ctx.beginPath();
          const r = Math.min(barWidth / 2, 2.5);
          ctx.moveTo(xPos + r, yPos);
          ctx.lineTo(xPos + barWidth - r, yPos);
          ctx.quadraticCurveTo(xPos + barWidth, yPos, xPos + barWidth, yPos + r);
          ctx.lineTo(xPos + barWidth, h);
          ctx.lineTo(xPos, h);
          ctx.lineTo(xPos, yPos + r);
          ctx.quadraticCurveTo(xPos, yPos, xPos + r, yPos);
          ctx.closePath();
          ctx.fill();
        }

        ctx.restore();
      }

      requestAnimationFrame(renderFrame);
    };

    requestAnimationFrame(renderFrame);
  }
};

export const render = (state, dispatch) => {
  const { x = 50, y = 220, w = 320, h = 120, isDragging, isResizing } = state || {};

  // Kick off visualizer loop on first render
  initVisualizerLoop();

  const handleMouseDown = (e) => {
    if (e.button !== 0) return;
    if (e.target.closest('[data-resize-handle="true"]')) return;

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
    zIndex: 999,
    cursor: isDragging ? 'grabbing' : isResizing ? 'se-resize' : 'grab',
    userSelect: 'none',
    WebkitUserSelect: 'none',
    boxSizing: 'border-box',
  };

  return (
    <div style={positionStyle} onMouseDown={handleMouseDown}>
      <div style={cardStyle}>
        {/* Visualizer Canvas */}
        <canvas id={CANVAS_ID} style={canvasStyle} />

        {/* Resize Handle in bottom-right corner */}
        <div
          data-resize-handle="true"
          style={resizeHandleStyle}
          onMouseDown={handleResizeStart}
          title="Drag to resize"
        >
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none" style={resizeSvgStyle}>
            <circle cx="8" cy="8" r="1" fill="rgba(255,255,255,0.4)" />
            <circle cx="8" cy="4" r="1" fill="rgba(255,255,255,0.4)" />
            <circle cx="4" cy="8" r="1" fill="rgba(255,255,255,0.4)" />
          </svg>
        </div>
      </div>
    </div>
  );
};

export const className = `
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color: #ffffff;

  [data-resize-handle="true"]:hover svg circle {
    fill: rgba(255, 255, 255, 0.85) !important;
  }
`;

const cardStyle = {
  position: 'relative',
  width: '100%',
  height: '100%',
  backgroundColor: 'rgba(24, 24, 28, 0.85)',
  backdropFilter: 'blur(30px) saturate(190%)',
  WebkitBackdropFilter: 'blur(30px) saturate(190%)',
  padding: '14px 16px 12px 16px',
  borderRadius: '20px',
  boxShadow: '0 16px 40px rgba(0, 0, 0, 0.55), 0 2px 6px rgba(0, 0, 0, 0.3)',
  border: '1px solid rgba(255, 255, 255, 0.12)',
  boxSizing: 'border-box',
  overflow: 'hidden',
  display: 'flex',
  flexDirection: 'column',
};

const canvasStyle = {
  width: '100%',
  height: '100%',
  display: 'block',
};

const resizeHandleStyle = {
  position: 'absolute',
  bottom: '0',
  right: '0',
  width: '18px',
  height: '18px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  cursor: 'se-resize',
  zIndex: 10,
};

const resizeSvgStyle = {
  pointerEvents: 'none',
};
