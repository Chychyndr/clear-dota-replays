from __future__ import annotations

import re
import sys
import winreg
from pathlib import Path


DOTA_APP_ID = "570"
TARGET_EXTENSION = ".edem"


def get_steam_path_from_registry() -> Path | None:
    """Пытается найти Steam через реестр Windows."""

    registry_locations = [
        (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
        (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "InstallPath"),
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WOW6432Node\Valve\Steam",
            "InstallPath",
        ),
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Valve\Steam",
            "InstallPath",
        ),
    ]

    for root, key_path, value_name in registry_locations:
        try:
            with winreg.OpenKey(root, key_path) as key:
                value, _ = winreg.QueryValueEx(key, value_name)

            path = Path(value)

            if path.exists():
                return path

        except (FileNotFoundError, OSError):
            continue

    return None


def find_steam_manually() -> Path | None:
    """Запасной поиск Steam в стандартных местах."""

    possible_paths = [
        Path(r"C:\Program Files (x86)\Steam"),
        Path(r"C:\Program Files\Steam"),
    ]

    for path in possible_paths:
        if path.exists():
            return path

    return None


def get_steam_libraries(steam_path: Path) -> list[Path]:
    """Получает список всех библиотек Steam."""

    libraries = {steam_path}

    library_file = steam_path / "steamapps" / "libraryfolders.vdf"

    if not library_file.exists():
        return list(libraries)

    try:
        content = library_file.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except OSError:
        return list(libraries)

    paths = re.findall(
        r'"path"\s*"([^"]+)"',
        content,
        flags=re.IGNORECASE,
    )

    for path_string in paths:
        # В VDF иногда используются экранированные обратные слэши
        path_string = path_string.replace(r"\\", "\\")

        path = Path(path_string)

        if path.exists():
            libraries.add(path)

    return list(libraries)


def get_dota_install_dir(library: Path) -> Path | None:
    """Ищет Dota 2 в конкретной библиотеке Steam."""

    manifest = (
        library
        / "steamapps"
        / f"appmanifest_{DOTA_APP_ID}.acf"
    )

    if not manifest.exists():
        return None

    try:
        content = manifest.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except OSError:
        return None

    match = re.search(
        r'"installdir"\s*"([^"]+)"',
        content,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    install_dir = (
        library
        / "steamapps"
        / "common"
        / match.group(1)
    )

    if install_dir.exists():
        return install_dir

    return None


def find_replay_folders(dota_path: Path) -> list[Path]:
    """
    Ищет возможные папки с реплеями.
    Основной современный путь:
    dota 2 beta/game/dota/replays
    """

    candidates = [
        dota_path / "game" / "dota" / "replays",
        dota_path / "dota" / "replays",
    ]

    return [
        path
        for path in candidates
        if path.exists() and path.is_dir()
    ]


def format_size(size: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]

    value = float(size)

    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.2f} {unit}"

        value /= 1024

    return f"{size} B"


def clean_edem_files(replay_folder: Path) -> tuple[int, int, int]:
    """
    Удаляет все .edem внутри replay_folder.

    Возвращает:
        deleted_count
        deleted_size
        failed_count
    """

    deleted_count = 0
    deleted_size = 0
    failed_count = 0

    for file in replay_folder.rglob("*"):
        if not file.is_file():
            continue

        if file.suffix.lower() != TARGET_EXTENSION:
            continue

        try:
            size = file.stat().st_size

            print(f"Удаляю: {file}")

            file.unlink()

            deleted_count += 1
            deleted_size += size

        except OSError as error:
            failed_count += 1

            print(
                f"Не удалось удалить:\n"
                f"  {file}\n"
                f"  Причина: {error}\n"
            )

    return deleted_count, deleted_size, failed_count


def main() -> None:
    print("Поиск Steam...")

    steam_path = get_steam_path_from_registry()

    if steam_path is None:
        steam_path = find_steam_manually()

    if steam_path is None:
        print("Steam не найден.")
        sys.exit(1)

    print(f"Steam найден: {steam_path}")

    libraries = get_steam_libraries(steam_path)

    print(f"Найдено библиотек Steam: {len(libraries)}")

    dota_paths: list[Path] = []

    for library in libraries:
        dota_path = get_dota_install_dir(library)

        if dota_path is not None:
            dota_paths.append(dota_path)

    if not dota_paths:
        print("Dota 2 не найдена.")
        sys.exit(1)

    total_deleted = 0
    total_size = 0
    total_failed = 0
    replay_folders_found = 0

    for dota_path in dota_paths:
        print()
        print(f"Dota 2 найдена: {dota_path}")

        replay_folders = find_replay_folders(dota_path)

        for replay_folder in replay_folders:
            replay_folders_found += 1

            print(f"Папка реплеев: {replay_folder}")
            print()

            deleted, size, failed = clean_edem_files(
                replay_folder
            )

            total_deleted += deleted
            total_size += size
            total_failed += failed

    print()
    print("=" * 50)

    if replay_folders_found == 0:
        print("Папка с реплеями не найдена.")
        return

    if total_deleted == 0:
        print("Файлов .edem не найдено.")
    else:
        print(f"Удалено файлов: {total_deleted}")
        print(f"Освобождено: {format_size(total_size)}")

    if total_failed:
        print(f"Не удалось удалить: {total_failed}")

    print("=" * 50)


if __name__ == "__main__":
    main()