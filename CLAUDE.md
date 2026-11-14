# Video factory — instructions for Claude

Owner: Ori (Hebrew speaker, no coding background, works from an Android phone). Talk to him in Hebrew without inline English.

## Making a new video
1. Create `videos/NN-short-name/` (next number).
2. `script.json` — see `videos/01-dud-shemesh/script.json`. Each scene: `id`, `say` (narration), optional `caption` (subtitle text if different), `min` (min seconds), `pause`, `rate`. Top level: `voice` (he-male, he-female, en-male, en-female, en-male-uk, en-female-uk or any edge-tts voice name), `lang` (he/en → RTL/LTR subtitles), `subtitles`, `width`/`height` (default 1080x1920 vertical), `fps`.
3. `animation.html` — include `../../factory/frame.css` and `../../factory/frame.js`. Define `window.init()` (build DOM/SVG once) and `window.drawScene(scene, p, t, info, local)` which must be a pure function of time (no CSS transitions, no setTimeout, no Math.random without a seed) — frames are rendered by seeking. Design surface is 540x960 CSS px (rendered at 2x). Keep the bottom ~180px clear for subtitles. Helpers on `window.H`: clamp, lerp, ease, span(local,a,b), $.
4. Test locally: `CHROME_PATH=/usr/bin/google-chrome python3 factory/build.py videos/NN-x --no-tts --fps 10`, then extract a few frames with ffmpeg and look at them.
5. Commit + push. The workflow `.github/workflows/build-video.yml` builds changed videos with real narration and commits `out/video.mp4` back. Fetch it (git pull) and send it to Ori.

## Rules
- Do not imitate real people's voices or copyrighted characters (e.g. Rick and Morty).
- Install only from official sources (apt, PyPI, Playwright).
