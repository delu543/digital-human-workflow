// Reviewed runtime adapters for Hyperframes 0.8.48 (Apache-2.0).
// No package files are overwritten; fail closed when upstream context changes.
import { registerHooks } from 'node:module';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const target = path.join(root, 'node_modules/hyperframes/dist/cli.js');
const version = JSON.parse(readFileSync(path.join(root, 'node_modules/hyperframes/package.json'))).version;
if (version !== '0.8.48') throw new Error('Hyperframes adapter requires reviewed version 0.8.48');

export function adapt(source, platform) {
  const capture = 'if (session.options.captureBeyondViewport) {';
  const sample = 'const times = assertions.length > 0 ? buildMotionSampleTimes2(motion.spec.duration ?? duration) : [];';
  for (const text of [capture, sample]) {
    if (source.split(text).length !== 2) throw new Error('Hyperframes adapter source mismatch');
  }
  // macOS tall portrait must retain the native-surface capture guard.
  if (platform === 'darwin') source = source.replace(capture,
    'if (session.options.captureBeyondViewport && process.platform !== "darwin") {');
  // Preserve all stock samples; add exact assertion deadlines to avoid skipping
  // short entrances/countdown digits on long films. Never remove assertions.
  return source.replace(sample,
    'const times = assertions.length > 0 ? mergeSampleTimes(buildMotionSampleTimes2(motion.spec.duration ?? duration), assertions.filter(a => a.kind === "appearsBy").flatMap(a => [Math.max(0, a.bySec - .02), a.bySec])) : [];');
}

registerHooks({load(url, context, nextLoad) {
  const result = nextLoad(url, context);
  if (!url.startsWith('file:') || fileURLToPath(url) !== target) return result;
  const source = typeof result.source === 'string' ? result.source : Buffer.from(result.source).toString();
  return {...result, source:adapt(source, process.platform)};
}});
