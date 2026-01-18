# VideoLingo Batch Mode

[English](./README.md) | [简体中文](./README.zh.md)

Batch process multiple videos for subtitle translation and dubbing.

## Prerequisites

Before using batch mode, ensure:
1. API keys are properly configured in `config.yaml`
2. Backend service is running (`start_backend.bat`)

## Usage

### 1. Prepare Video Files

- Place video files in `batch/input` folder

### 2. Configure Tasks

Edit `tasks_setting.xlsx`:

| Field | Description | Values |
|-------|-------------|--------|
| Video File | Video filename (without `input/` prefix) | - |
| Source Language | Source language | 'en', 'zh', ... or empty for default |
| Target Language | Translation target | Natural language description, or empty for default |
| Dubbing | Enable dubbing | 0 or empty: subtitles only; 1: subtitles + dubbing |
| Status | Task status (auto-filled) | Done / Error: ... |

Example:

| Video File | Source Language | Target Language | Dubbing | Status |
|------------|-----------------|-----------------|---------|--------|
| video1.mp4 | en | 简体中文 | 0 | |
| video2.mp4 | ja | English | 1 | |
| video3.mp4 | | | 1 | Done |

### 3. Start Backend Service

In one terminal window:
```bash
# Windows
.\start_backend.bat

# PowerShell
.\start_backend.ps1
```

### 4. Run Batch Processing

In another terminal:
```bash
# From batch directory
cd batch
OneKeyBatch.bat
```

Or from project root:
```bash
python -m batch.utils.batch_processor
```

### 5. Check Results

- Successful outputs saved to `batch/output/{video_name}/`
- Failed outputs saved to `batch/output/ERROR/{video_name}/`
- Task status recorded in `tasks_setting.xlsx` Status column

> ⚠️ Note: Keep `tasks_setting.xlsx` closed while running, otherwise status cannot be saved.

## Error Handling

### Retry Failed Tasks

If a task fails (Status shows `Error: ...`):
1. Check and fix the issue (API quota, network, etc.)
2. Re-run `OneKeyBatch.bat`
3. Program will automatically restore files from ERROR folder and continue

### Skip Completed Tasks

Tasks with `Done` status are automatically skipped. To reprocess, clear the Status cell.

## Directory Structure

```
batch/
├── input/              # Place video files here
├── output/             # Processed outputs
│   ├── video1/         # Successful output
│   └── ERROR/          # Failed output (for retry)
│       └── video2/
├── tasks_setting.xlsx  # Task configuration
├── OneKeyBatch.bat     # One-click launcher
└── utils/
    └── batch_processor.py  # Core batch logic
```
