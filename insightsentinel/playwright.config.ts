import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E Test Configuration for InsightSentinel
 *
 * Run tests with: npm test
 * Run with UI: npm run test:ui
 * Run headed: npm run test:headed
 *
 * Before running tests, ensure:
 * 1. Frontend is running: npm run dev
 * 2. Backend is running: cd ../backend && uv run uvicorn app.main:app --port 8000
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [['html'], ['list']],

  // Increase timeout for SSE-based tests
  timeout: 60000,

  use: {
    // Base URL for all tests
    baseURL: process.env.FRONTEND_URL || 'http://localhost:5173',

    // Collect trace when retrying the failed test
    trace: 'on-first-retry',

    // Screenshot on failure
    screenshot: 'only-on-failure',

    // Video on failure
    video: 'retain-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // Don't auto-start servers - assume they're already running
  // To auto-start, uncomment and run: npm run test:auto
  // webServer: [
  //   {
  //     command: 'npm run dev',
  //     url: 'http://localhost:5173',
  //     reuseExistingServer: true,
  //     timeout: 120000,
  //   },
  //   {
  //     command: 'cd ../backend && uv run uvicorn app.main:app --port 8000',
  //     url: 'http://localhost:8000/health',
  //     reuseExistingServer: true,
  //     timeout: 120000,
  //   },
  // ],
});
