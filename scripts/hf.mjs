import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { existsSync } from 'node:fs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const env={...process.env,DO_NOT_TRACK:'1',HYPERFRAMES_NO_TELEMETRY:'1'};
delete env.MINIMAX_API_KEY;
delete env.HEYGEN_API_KEY;
// Reuse an installed Chrome when available; avoid an unnecessary large first-render download.
if (!env.HYPERFRAMES_BROWSER_PATH) {
  const candidates=process.platform==='darwin'
    ? ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome']
    : process.platform==='win32'
      ? [env.PROGRAMFILES,env['PROGRAMFILES(X86)'],env.LOCALAPPDATA].filter(Boolean).map(p=>path.join(p,'Google','Chrome','Application','chrome.exe'))
      : ['/usr/bin/google-chrome','/usr/bin/google-chrome-stable','/usr/bin/chromium','/usr/bin/chromium-browser'];
  const browser=candidates.find(p=>existsSync(p));
  if (browser) env.HYPERFRAMES_BROWSER_PATH=browser;
}
env.PATH=[path.join(root,'.runtime','bin'),env.PATH].join(path.delimiter);
const child=spawn(process.execPath,[path.join(root,'node_modules','hyperframes','bin','hyperframes.mjs'),...process.argv.slice(2)],{env,stdio:'inherit'});
child.on('error',()=>{console.error('本地 Hyperframes 不可用，请运行 bootstrap.py');process.exitCode=1;});
child.on('exit',code=>{process.exitCode=code??1;});
