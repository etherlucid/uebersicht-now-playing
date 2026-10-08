// CAVA Widget Configuration
// Edit colors, gradient stops, and visualizer settings here.

export const theme = {
  // Window frame appearance (matches your iTerm2 Gruvbox profile)
  bg: 'rgba(28, 27, 25, 0.90)',
  cardBorder: 'rgba(255, 255, 255, 0.12)',
  titleColor: 'rgba(252, 232, 195, 0.70)',
  statusColor: 'rgba(252, 232, 195, 0.40)',

  // Vertical frequency bar gradient (matching ~/.config/cava/config)
  // Ordered from bottom (low amplitude) to top (peak amplitude)
  gradient: [
    '#59cc33', // 1: Green base
    '#80cc33', // 2
    '#a6cc33', // 3
    '#cccc33', // 4: Yellow mid
    '#cca633', // 5
    '#cc8033', // 6
    '#cc5933', // 7
    '#cc3333', // 8: Red peak
  ],

  // Glow shadow behind active bars
  barGlow: 'rgba(89, 204, 51, 0.25)',
};

export const settings = {
  title: 'cava',
  barsCount: 28,
  barGap: 3,          // Gap in pixels between bars
  minBarHeightPct: 2, // Height percentage of idle bar heads
};

export default { theme, settings };
