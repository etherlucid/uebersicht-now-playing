// Shell Widget Configuration
// Edit window appearance, prompt, and ANSI terminal colors here.

export const theme = {
  // Window frame appearance (matches your iTerm2 Gruvbox profile)
  bg: 'rgba(28, 27, 25, 0.90)',
  cardBorder: 'rgba(255, 255, 255, 0.12)',
  fg: '#fce8c3',
  cursor: '#fbb829',
  selection: '#fce8c3',

  // 16-Color ANSI Terminal Palette
  black: '#1c1b19',
  red: '#ef2f27',
  green: '#519f50',
  yellow: '#fbb829',
  blue: '#2c78bf',
  magenta: '#e02c6d',
  cyan: '#0aaeb3',
  white: '#baa67f',

  // Bright ANSI variants
  brightBlack: '#918175',
  brightRed: '#f75341',
  brightGreen: '#98bc37',
  brightYellow: '#fed06e',
  brightBlue: '#68a8e4',
  brightMagenta: '#ff5c8f',
  brightCyan: '#2be4d0',
  brightWhite: '#fce8c3',
};

export const settings = {
  // Window appearance (matches cava.widget)
  showTitleBar: false, // Set to true to restore the window titlebar
  title: 'zsh',

  // Typography
  fontSize: '11px',
  lineHeight: '1.35',

  // Single command mode:
  // Concise fastfetch layout (key specs aligned to Apple ASCII logo without verbose clutter):
  command: 'fastfetch -s Break:Break:Break:Title:Separator:OS:Host:Kernel:Uptime:Packages:Shell:CPU:GPU:Memory:Battery',
  // Alternative presets:
  // command: 'fastfetch -c neofetch', // Neofetch layout
  // command: 'fastfetch',             // Full verbose default
  // command: '',                      // Interactive shell prompt

  // Refresh frequency for single command mode:
  // false = run once on load; or set to milliseconds (e.g. 60000 for 1 min, 300000 for 5 min)
  refreshFrequency: false,

  // Prompt settings (used when command is empty)
  promptSymbol: '❯',
  placeholder: 'run command...',
  timeoutSeconds: 15,
};

export default { theme, settings };
