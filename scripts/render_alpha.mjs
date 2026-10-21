#!/usr/bin/env node
// Deterministic local HTML graphics -> silent QTRLE/ARGB MOV. No package installation.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';
import {spawn} from 'node:child_process';
import {once} from 'node:events';

const usage = 'node render_alpha.mjs --html FILE --output FILE.mov --width N --height N --fps 30|30000/1001 --duration SECONDS --ffmpeg PATH [--playwright-from /existing/project/package.json]';
function options(argv) {
  if (argv.includes('--help')) { console.log(usage); process.exit(0); }
  const allowed = new Set(['html', 'output', 'width', 'height', 'fps', 'duration', 'ffmpeg', 'playwright-from']);
  const opts = {};
  for (let i = 0; i < argv.length; i += 2) {
    const key = argv[i].slice(2);
    if (!argv[i].startsWith('--') || !allowed.has(key) || !argv[i + 1] || opts[key]) throw Error(usage);
    opts[key] = argv[i + 1];
  }
  for (const key of ['html', 'output', 'width', 'height', 'fps', 'duration', 'ffmpeg']) {
    if (!opts[key]) throw Error(`Missing --${key}\n${usage}`);
  }
  return opts;
}
function fraction(value) {
  if (!/^\d+(?:\.\d+)?(?:\/\d+(?:\.\d+)?)?$/.test(value)) throw Error(`Invalid positive number: ${value}`);
  const [numerator, denominator = '1'] = value.split('/').map(Number);
  const result = numerator / Number(denominator);
  if (!Number.isFinite(result) || result <= 0) throw Error(`Invalid positive number: ${value}`);
  return result;
}

async function main() {
  const opts = options(process.argv.slice(2));
  const width = Number(opts.width), height = Number(opts.height);
  const fps = fraction(opts.fps), duration = fraction(opts.duration);
  if (![width, height].every(x => Number.isSafeInteger(x) && x > 0)) throw Error('Width and height must be positive integers');
  const html = path.resolve(opts.html), output = path.resolve(opts.output);
  if (path.extname(output).toLowerCase() !== '.mov') throw Error('Alpha output must have .mov extension');
  fs.accessSync(html, fs.constants.R_OK);
  fs.accessSync(path.resolve(opts.ffmpeg), fs.constants.X_OK);
  if (fs.existsSync(output)) throw Error(`Output already exists; choose a new filename: ${output}`);
  const require = createRequire(path.resolve(opts['playwright-from'] || path.join(process.cwd(), 'package.json')));
  const {chromium} = require('playwright');
  fs.accessSync(chromium.executablePath(), fs.constants.X_OK);
  const frames = Math.ceil(duration * fps - 1e-9);
  fs.mkdirSync(path.dirname(output), {recursive: true});
  const browser = await chromium.launch({headless: true, args: ['--allow-file-access-from-files']});
  let encoder;
  try {
    const page = await browser.newPage({viewport: {width, height}, deviceScaleFactor: 1});
    let pageError;
    page.on('pageerror', error => { pageError = error; });
    await page.route('**/*', route => {
      const protocol = new URL(route.request().url()).protocol;
      return ['file:', 'data:', 'blob:', 'about:'].includes(protocol) ? route.continue() : route.abort();
    });
    await page.goto(pathToFileURL(html).href, {waitUntil: 'load'});
    await page.evaluate(async () => {
      if (document.querySelector('video, audio')) throw Error('Use a media-aware renderer for HTML video/audio; this helper renders local graphics only');
      await window.ready;
      await document.fonts.ready;
      await Promise.all([...document.images].map(img => img.decode()));
      if (typeof window.renderAt !== 'function') throw Error('HTML must implement window.renderAt(t)');
    });
    if (pageError) throw pageError;
    encoder = spawn(path.resolve(opts.ffmpeg), [
      '-n', '-v', 'error', '-f', 'image2pipe', '-framerate', opts.fps,
      '-vcodec', 'png', '-i', 'pipe:0', '-an', '-c:v', 'qtrle', '-pix_fmt', 'argb', output,
    ], {stdio: ['pipe', 'ignore', 'pipe']});
    let stderr = '', encoderError, inputError;
    encoder.stderr.on('data', buffer => { stderr = (stderr + buffer.toString()).slice(-65536); });
    encoder.on('error', error => { encoderError = error; });
    encoder.stdin.on('error', error => { inputError = error; });
    const finished = new Promise(resolve => encoder.once('close', code => resolve(code)));
    for (let frame = 0; frame < frames; frame++) {
      if (encoderError || inputError || encoder.exitCode !== null) throw encoderError || inputError || Error(stderr || 'FFmpeg exited early');
      await page.evaluate(t => window.renderAt(t), frame / fps);
      if (pageError) throw pageError;
      const png = await page.screenshot({omitBackground: true, animations: 'allow'});
      if (!encoder.stdin.write(png)) await once(encoder.stdin, 'drain');
      if ((frame + 1) % Math.max(1, Math.round(fps * 5)) === 0) console.log(`Rendered ${frame + 1}/${frames} frames`);
    }
    encoder.stdin.end();
    const code = await finished;
    if (encoderError || inputError || code !== 0) throw encoderError || inputError || Error(stderr || `FFmpeg exited ${code}`);
    if (!fs.statSync(output).size) throw Error('Output is empty');
    console.log(JSON.stringify({output, width, height, fps: opts.fps, frames,
      duration: frames / fps, codec: 'qtrle', pixel_format: 'argb', audio: false}));
  } finally {
    if (encoder && encoder.exitCode === null && encoder.signalCode === null) encoder.kill();
    await browser.close();
  }
}

main().catch(error => { console.error(`Error: ${error.message}`); process.exitCode = 1; });
