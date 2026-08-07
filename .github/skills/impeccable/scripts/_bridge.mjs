import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..', '..');

export function resolveScript(scriptName) {
  const candidates = [
    path.join(repoRoot, '.codex', 'skills', 'impeccable', 'scripts', scriptName),
    path.join(repoRoot, '.agents', 'skills', 'impeccable', 'scripts', scriptName),
    process.env.CODEX_HOME
      ? path.join(process.env.CODEX_HOME, 'skills', 'impeccable', 'scripts', scriptName)
      : null,
    path.join(os.homedir(), '.codex', 'skills', 'impeccable', 'scripts', scriptName),
    path.join(os.homedir(), '.agents', 'skills', 'impeccable', 'scripts', scriptName),
  ].filter(Boolean);

  const resolved = candidates.find((candidate) => fs.existsSync(candidate));
  if (!resolved) {
    throw new Error(
      `Impeccable script not found: ${scriptName}. Install the impeccable skill in .codex/skills or .agents/skills.`,
    );
  }
  return resolved;
}

export function run(scriptName) {
  const result = spawnSync(process.execPath, [resolveScript(scriptName), ...process.argv.slice(2)], {
    cwd: process.cwd(),
    stdio: 'inherit',
  });
  if (result.error) throw result.error;
  process.exitCode = result.status ?? 1;
}
