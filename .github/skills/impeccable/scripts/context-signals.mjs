import fs from 'node:fs';
import net from 'node:net';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { resolveScript } from './_bridge.mjs';

const result = spawnSync(process.execPath, [resolveScript('context-signals.mjs'), ...process.argv.slice(2)], {
  cwd: process.cwd(),
  encoding: 'utf8',
});

if (result.error) throw result.error;
if (result.status !== 0) {
  process.stderr.write(result.stderr || 'Unable to gather Impeccable context signals.\n');
  process.exit(result.status ?? 1);
}

const signals = JSON.parse(result.stdout);
const cwd = process.cwd();
const jinjaDirs = ['templates', 'static'].filter((dir) => fs.existsSync(path.join(cwd, dir)));

if (jinjaDirs.length) {
  signals.setup.hasCode = true;
  if (!signals.scan.targets.length) {
    signals.scan = { targets: jinjaDirs, via: 'fastapi-jinja' };
  }
}

const port8010Open = await new Promise((resolve) => {
  const socket = new net.Socket();
  const finish = (open) => {
    socket.destroy();
    resolve(open);
  };
  socket.setTimeout(250);
  socket.once('connect', () => finish(true));
  socket.once('timeout', () => finish(false));
  socket.once('error', () => finish(false));
  socket.connect(8010, '127.0.0.1');
});

if (port8010Open && !signals.devServer.ports.includes(8010)) {
  signals.devServer.ports.push(8010);
  signals.devServer.ports.sort((a, b) => a - b);
  signals.devServer.running = true;
}

process.stdout.write(`${JSON.stringify(signals, null, 2)}\n`);
