#!/usr/bin/env node
const { spawn } = require('child_process');
const path = require('path');

const frontendDir = path.join(__dirname, 'frontend');
const configPath = path.join(__dirname, 'playwright.config.js');

const child = spawn('node', [
  './node_modules/@playwright/test/cli.js',
  '-c', configPath,
  '--project=chromium'
], {
  cwd: frontendDir,
  stdio: 'inherit',
  env: {
    ...process.env,
    NODE_PATH: path.join(frontendDir, 'node_modules')
  }
});

child.on('close', (code) => {
  process.exit(code);
});