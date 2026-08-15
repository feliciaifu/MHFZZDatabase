'use strict';
// 开发模式：先启动 Vite dev server，再启动 Electron
const { spawn } = require('child_process');
const electron = require('electron');

const DEV_URL = 'http://localhost:5173';

async function waitForVite(timeoutMs = 30000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(DEV_URL);
      if (res.ok) return true;
    } catch { /* not ready yet */ }
    await new Promise((r) => setTimeout(r, 300));
  }
  return false;
}

(async () => {
  const vite = spawn('npx', ['vite', '--config', 'renderer/vite.config.js'], {
    stdio: 'inherit',
    shell: true,
  });
  vite.on('close', (code) => process.exit(code || 1));

  const ok = await waitForVite();
  if (!ok) {
    console.error('[dev] Vite 未在 ' + DEV_URL + ' 就绪，请检查端口占用');
    vite.kill();
    process.exit(1);
  }
  console.log('[dev] Vite 就绪: ' + DEV_URL);
  const child = spawn(electron, ['.', '--remote-debugging-port=9222'], {
    stdio: 'inherit',
    env: { ...process.env, VITE_DEV_SERVER_URL: DEV_URL },
  });
  child.on('close', () => {
    vite.kill();
    process.exit(0);
  });
})();
