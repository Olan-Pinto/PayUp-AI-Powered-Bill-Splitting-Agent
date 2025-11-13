const API_URL = import.meta.env.VITE_API_URL || 'https://payup-api-332078128555.us-central1.run.app';

// For WebSocket connections
const WS_URL = API_URL.replace('https://', 'wss://').replace('http://', 'ws://');

export { API_URL, WS_URL };