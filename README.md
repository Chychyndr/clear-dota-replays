# Dota 2 EDEM Cleaner

A simple Windows script that automatically locates your Dota 2 installation and removes all `.edem` replay files.

## Usage

```powershell
uv run clean_dota_edem.py
```

The script automatically:

- Locates Steam and Dota 2.
- Finds the replay directories.
- Deletes all `.edem` files.
- Reports how many files were deleted and how much disk space was freed.

Regular `.dem` replay files are preserved.
