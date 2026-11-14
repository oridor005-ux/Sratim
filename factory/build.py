#!/usr/bin/env python3
"""מפעל הסרטונים — בונה סרטון מתיקייה אחת.

תיקיית סרטון מכילה:
  script.json     — הגדרות + רשימת סצנות (טקסט קריינות לכל סצנה)
  animation.html  — האנימציה. חושפת window.drawScene(scene, p, t, info)

שלבים:
  1. קריינות: כל סצנה הופכת לקובץ קול (edge-tts, קולות חינמיים)
  2. ציר זמן: אורך כל סצנה נקבע לפי אורך הקריינות שלה
  3. צילום: דפדפן נסתר מצייר כל פריים (30 בשנייה) ושומר תמונה
  4. הרכבה: ffmpeg מחבר תמונות + קול -> out/video.mp4

שימוש:
  python factory/build.py videos/01-dud-shemesh
  python factory/build.py videos/01-dud-shemesh --no-tts   (בדיקה בלי קול)
"""
import argparse, asyncio, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent

VOICES = {
    # עברית
    "he-male": "he-IL-AvriNeural",
    "he-female": "he-IL-HilaNeural",
    # אנגלית
    "en-male": "en-US-GuyNeural",
    "en-female": "en-US-JennyNeural",
    "en-male-uk": "en-GB-RyanNeural",
    "en-female-uk": "en-GB-SoniaNeural",
}


def run(cmd):
    subprocess.run(cmd, check=True)


def probe_duration(path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1", str(path)])
    return float(out.strip())


async def tts(text, voice, rate, pitch, out_path):
    import edge_tts
    last = None
    for attempt in range(4):
        try:
            com = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
            await com.save(str(out_path))
            if out_path.stat().st_size > 1000:
                return
        except Exception as e:  # השירות לפעמים נכשל זמנית
            last = e
        await asyncio.sleep(2 + attempt * 3)
    raise RuntimeError(f"קריינות נכשלה: {last}")


def make_silence(seconds, out_path):
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
         "anullsrc=r=24000:cl=mono", "-t", f"{seconds:.3f}", "-c:a",
         "libmp3lame", "-q:a", "4", str(out_path)])


def build(folder, no_tts=False, fps=None, limit=None):
    folder = Path(folder).resolve()
    cfg = json.loads((folder / "script.json").read_text(encoding="utf-8"))
    width = cfg.get("width", 1080)
    height = cfg.get("height", 1920)
    fps = fps or cfg.get("fps", 30)
    voice = VOICES.get(cfg.get("voice", "he-male"), cfg.get("voice"))
    rate = cfg.get("rate", "+0%")
    pitch = cfg.get("pitch", "+0Hz")
    pad = cfg.get("pause", 0.5)  # שקט אחרי כל סצנה
    lead = cfg.get("lead_in", 0.6)  # שקט לפני הקריינות הראשונה

    work = Path(tempfile.mkdtemp(prefix="vid-"))
    audio_parts = []
    timeline = []
    t = 0.0

    # שקט פתיחה
    if lead > 0:
        p = work / "lead.mp3"
        make_silence(lead, p)
        audio_parts.append(p)
        t += lead

    for i, sc in enumerate(cfg["scenes"]):
        text = sc.get("say", "").strip()
        mp3 = work / f"s{i:02d}.mp3"
        if text and not no_tts:
            asyncio.run(tts(text, voice, sc.get("rate", rate), pitch, mp3))
            dur = probe_duration(mp3)
        else:
            # בלי קול: הערכה לפי אורך הטקסט (בערך 13 תווים לשנייה)
            dur = sc.get("min", max(2.0, len(text) / 13.0))
            make_silence(dur, mp3)
        dur = max(dur, sc.get("min", 0))
        audio_parts.append(mp3)
        gap = sc.get("pause", pad)
        if gap > 0:
            g = work / f"g{i:02d}.mp3"
            make_silence(gap, g)
            audio_parts.append(g)
        start = t - (lead if i == 0 else 0)  # הסצנה הראשונה מתחילה ב־0
        end = t + dur + gap
        timeline.append({"i": i, "id": sc.get("id", f"s{i}"), "start": round(start, 3),
                         "speechStart": round(t, 3), "speechEnd": round(t + dur, 3),
                         "end": round(end, 3), "say": text, "caption": sc.get("caption", text)})
        t = end

    total = t + cfg.get("tail", 0.8)
    timeline[-1]["end"] = round(total, 3)

    # חיבור הקול
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in audio_parts))
    audio = work / "audio.m4a"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
         "-af", f"apad=whole_dur={total:.3f}", "-c:a", "aac", "-b:a", "160k", str(audio)])

    # צילום הפריימים
    frames = work / "frames"
    frames.mkdir()
    n = int(round(total * fps))
    if limit:
        n = min(n, int(limit * fps))
    info = {"width": width, "height": height, "total": total, "fps": fps,
            "title": cfg.get("title", ""), "subtitles": cfg.get("subtitles", True),
            "lang": cfg.get("lang", "he")}
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        exe = os.environ.get("CHROME_PATH")
        browser = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        page = browser.new_page(viewport={"width": width // 2, "height": height // 2},
                                device_scale_factor=2)
        page.goto((folder / "animation.html").as_uri())
        page.wait_for_function("window.__ready === true", timeout=20000)
        page.evaluate("([tl, info]) => window.__setup(tl, info)", [timeline, info])
        page.evaluate("document.fonts.ready")
        for f in range(n):
            page.evaluate("(t) => window.__seek(t)", f / fps)
            page.screenshot(path=str(frames / f"{f:05d}.jpg"), type="jpeg", quality=90)
            if f % (fps * 5) == 0:
                print(f"  פריים {f}/{n}", flush=True)
        browser.close()

    out_dir = folder / "out"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / "video.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i",
         str(frames / "%05d.jpg"), "-i", str(audio), "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "21", "-pix_fmt", "yuv420p", "-c:a", "copy", "-shortest",
         "-movflags", "+faststart", str(out)])
    (out_dir / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=1),
                                           encoding="utf-8")
    shutil.rmtree(work, ignore_errors=True)
    print(f"מוכן: {out} ({total:.1f} שניות)")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--no-tts", action="store_true")
    ap.add_argument("--fps", type=int)
    ap.add_argument("--limit", type=float, help="לבנות רק את X השניות הראשונות")
    a = ap.parse_args()
    build(a.folder, a.no_tts, a.fps, a.limit)
