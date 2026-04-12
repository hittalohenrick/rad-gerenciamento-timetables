const { execSync } = require('node:child_process');

module.exports = async () => {
  const e2eDatabaseUrl = process.env.E2E_DATABASE_URL || 'sqlite:////tmp/rad_timetables_playwright.db';
  const env = {
    ...process.env,
    DATABASE_URL: e2eDatabaseUrl,
  };

  execSync('.venv/bin/python scripts/seed_playwright_data.py', {
    stdio: 'inherit',
    env,
  });
};
