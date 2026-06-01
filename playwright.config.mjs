import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 90_000,
  retries: 0,
  use: {
    baseURL: 'http://localhost:3000',
    headless: true,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      // Backend
      command: 'cd backend && .venv/bin/uvicorn app.main:app --port 8000',
      url: 'http://localhost:8000/docs',
      reuseExistingServer: true,
      timeout: 30_000,
    },
    {
      // Frontend static server
      command: 'python3 -m http.server 3000 --directory frontend',
      url: 'http://localhost:3000',
      reuseExistingServer: true,
      timeout: 10_000,
    },
  ],
});
