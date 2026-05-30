# Native Analytics Vizro

A data visualization dashboard project built with [Vizro](https://vizro.readthedocs.io/).

## Setup

### 1. Create and activate virtual environment

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the app

```bash
python app.py
```

Then open http://localhost:8050 in your browser.

## Project Structure

```
.
├── app.py            # Main application entry point
├── requirements.txt  # Python dependencies
├── assets/           # Static assets (CSS, images, custom JS)
└── pages/            # Additional dashboard pages (optional)
```

## Dependencies

- [Vizro](https://github.com/mckinsey/vizro) — low-code dashboard framework built on Dash & Plotly
- Python 3.11+
