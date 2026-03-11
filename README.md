# Elite Image Mapper

Elite Image Mapper renames Elite Dangerous screenshots by matching them against the game's journal files.
It can also optionally convert the images to another format such as PNG, JPEG, or WEBP.

## Features

- Match screenshots to Elite Dangerous journal entries
- Rename images with:
  - date
  - time
  - star system
  - planet / body when available
- Mark HighRes screenshots with `HR`
- Optional image conversion:
  - PNG
  - JPEG
  - WEBP
- Optional deletion of originals after successful processing

## Supported image sources

- Elite Dangerous screenshots
- Steam screenshots
- BMP, JPG/JPEG, PNG, WEBP

## How it works

The tool compares the image timestamps and filenames with the Elite Dangerous journal timeline.
For many Elite screenshots, the journal `Screenshot` event is the strongest source because it can contain the screenshot filename, system, and body.
If that is not available, the app falls back to other journal events such as location and approach/body events.

## Run from source (without `.exe`)

### Requirements

- Python 3.11 or newer recommended
- `Pillow` only if you want image conversion

### 1. Clone the repository

```bash
git clone https://github.com/LouisH99/EliteImageMapper.git
cd EliteImageMapper
```

### 2. Create a virtual environment

**Windows**

```bash
python -m venv .venv
.venv\Scripts\activate
```

**Linux / macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install optional dependencies

If you want conversion support:

```bash
pip install pillow
```

### 4. Start the GUI

```bash
python EliteImageMapper.py --gui
```

## Default folder suggestions

On Windows the GUI suggests these default folders when available:

- Screenshots: `C:\Users\<YourUser>\Pictures\Frontier Developments\Elite Dangerous`
- Journals: `C:\Users\<YourUser>\Saved Games\Frontier Developments\Elite Dangerous`

You can change all folders in the GUI.

## Output

The processed files are written into the output folder selected in the GUI.
A CSV report is also created:

- `mapping_report.csv`

## Build a portable Windows `.exe`

A portable Windows build can be created with **PyInstaller**.
This is useful for users who do not want to install Python.

Typical steps:

```bash
pip install pyinstaller pillow
pyinstaller --noconfirm --distpath . --workpath build EliteImageMapper.spec
```

The finished app folder will be created directly as:

```text
EliteImageMapper
```

Start the program by opening:

```text
EliteImageMapper\EliteImageMapper.exe
```

## Notes

- If conversion is disabled, the app only renames and copies files.
- Original images are only deleted when that option is enabled and the output file was written successfully.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - feel free to use and modify as needed.
