import sounddevice as sd
import numpy as np
import subprocess
import queue
import tempfile
import soundfile as sf
from openai import OpenAI
import os

client = OpenAI()

WAKE_WORD = "sage"  # Say "Sage ..." to trigger it

def record_audio(duration=50, samplerate=16000):
    input("👉 Press Enter when you’re ready to start talking…")
    print("🎙️  Recording… speak now!")
    import time
    time.sleep(5)
    q = queue.Queue()

    def callback(indata, frames, time, status):
        q.put(indata.copy())

    with sd.InputStream(samplerate=samplerate, channels=1, callback=callback):
        frames = []
        for _ in range(int(duration * samplerate / 1024)):
            frames.append(q.get())
        audio_data = np.concatenate(frames, axis=0).flatten()

    print("✅  Recording complete.")
    return audio_data, samplerate


def transcribe_with_whisper(audio_data, samplerate):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        sf.write(tmp.name, audio_data, samplerate)
        tmp_path = tmp.name

    print("🗣️  Transcribing with Whisper...")
    with open(tmp_path, "rb") as f:
        transcript = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=f,
            temperature=0  # makes it less "creative"
        )
    os.remove(tmp_path)
    text = transcript.text.strip()
    print(f"👉 You said: {text}")
    return text.lower()


def parse_command(cmd):
    role = "product manager"
    location = "los angeles"
    threshold = 70
    words = cmd.split()

    if "in" in words:
        idx = words.index("in")
        if idx + 1 < len(words):
            location = " ".join(words[idx + 1:])
    if "above" in words:
        idx = words.index("above")
        if idx + 1 < len(words):
            try:
                threshold = int(words[idx + 1])
            except ValueError:
                pass

    if "product" in cmd:
        role = "product manager"
    elif "data" in cmd:
        role = "data analyst"

    return role, location, threshold


def main():
    audio_data, samplerate = record_audio()
    cmd = transcribe_with_whisper(audio_data, samplerate)

    if WAKE_WORD not in cmd:
        print(f"🛑 I didn’t hear my name (‘{WAKE_WORD}’) — not running a search.")
        return

    role, location, thresh = parse_command(cmd)
    print(f"🔎 Searching for {role.title()} jobs in {location.title()} ≥{thresh}% match")
    subprocess.run(["python3", "job_scraper.py"])


if __name__ == "__main__":
    main()
