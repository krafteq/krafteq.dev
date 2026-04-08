# 📹 AI Camera Diary Log

An AI-powered camera monitoring system that analyzes live video feeds and logs observations about objects, people, and actions using a local vision LLM.

---

## Requirements

- Python 3.11+
- [Ollama](https://ollama.com) installed and running
- IP camera (RTSP) or USB webcam

---

## Installation

**1. Clone the repo and create a virtual environment**
```bash
git clone <repo-url>
cd <project>
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Pull the vision model**
```bash
ollama pull llava
# or for faster CPU performance:
ollama pull moondream
```

---

## Configuration

**1. Copy the example env file and fill in your values**
```bash
cp .env.example .env
```

Key settings in `.env`:
```env
LLM_MODEL=llava           # or moondream
ANALYSIS_INTERVAL=10      # seconds between LLM analysis
CAMERA_MODE=single        # single | multi (future)
```

**2. Edit `cameras.yaml` to set up your camera**

For an IP camera:
```yaml
- name: "Front Door"
  type: ip
  ip: 192.168.0.60
  user: admin
  password: admin
  port: 554
  stream: "0"
  active: true
```

For a USB webcam:
```yaml
- name: "USB Webcam"
  type: usb
  device_index: 0
  active: true
```

Only the **first** camera with `active: true` runs in single mode.

---

## Usage

```bash
python src/main.py
```

- A window opens showing the live feed
- Every `ANALYSIS_INTERVAL` seconds, the frame is analyzed
- Observations are printed to the terminal and saved to `detector.log`
- Press **`q`** to quit

---

## Project Structure

```
project/
├── src/
│   ├── main.py        ← entry point
│   ├── detector.py    ← camera + LLM pipeline
│   └── config.py      ← settings loader
├── cameras.yaml       ← camera definitions
├── .env               ← your secrets (never commit!)
├── .env.example       ← safe to commit
├── requirements.txt
└── detector.log       ← auto-generated
```