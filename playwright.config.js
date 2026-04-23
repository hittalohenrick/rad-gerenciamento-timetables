const path = require('node:path');
const { defineConfig, devices } = require('@playwright/test');

const E2E_DATABASE_URL = process.env.E2E_DATABASE_URL || 'sqlite:////tmp/rad_timetables_playwright.db';

module.exports = defineConfig({
  testDir: path.join(__dirname, 'tests/e2e'),
  timeout: 60_000,
  expect: {
    timeout: 8_000,
  },
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [
    ['list'],
    ['html', { open: 'never', outputFolder: 'playwright-report' }],
  ],
  use: {
    baseURL: 'http://127.0.0.1:5010',
    headless: true,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: process.env.PW_VIDEO_MODE || 'retain-on-failure',
  },
  globalSetup: require.resolve('./tests/e2e/global-setup.js'),
  webServer: {
    command: ".venv/bin/python -c \"from app import create_app; app=create_app(); app.run(host='127.0.0.1', port=5010)\"",
    url: 'http://127.0.0.1:5010/login',
    timeout: 120_000,
    reuseExistingServer: false,
    env: {
      ...process.env,
      DATABASE_URL: E2E_DATABASE_URL,
      FLASK_DEBUG: '0',
    },
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
