#!/usr/bin/env node

import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(__dirname, '..');

const args = process.argv.slice(2);
const command = args[0];
const inputFile = args.find(arg => arg.startsWith('--input='))?.split('=')[1];

if (command === 'parse-prd' && inputFile) {
  const taskMasterPath = path.resolve(projectRoot, 'node_modules/.bin/task-master');
  const child = spawn(taskMasterPath, ['parse-prd', `--input=${inputFile}`], {
    stdio: 'inherit',
    env: {
      ...process.env,
      NODE_PATH: path.resolve(projectRoot, 'node_modules')
    }
  });

  child.on('error', (error) => {
    console.error('Failed to start task-master:', error);
    process.exit(1);
  });

  child.on('exit', (code) => {
    process.exit(code);
  });
} else {
  console.error('Usage: node task-master.js parse-prd --input=<prd-file>');
  process.exit(1);
} 