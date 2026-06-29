import os
import re
import threading
import time

import requests

LOKI_URL = "http://localhost:3100/loki/api/v1/push"
JOB_NAME = "minecraft-logs"

LOG_SOURCES = {
    "escape": "./escape/logs/latest.log",
    "survival": "./survival/logs/latest.log",
}

CATEGORY_PATTERNS = [
    ("join", re.compile(r"\bjoined the game\b", re.IGNORECASE)),
    ("leave", re.compile(r"\bleft the game\b", re.IGNORECASE)),
    ("gamemode", re.compile(r"\b(game mode|gamemode)\b", re.IGNORECASE)),
    ("advancement", re.compile(r"\bhas made the advancement\b", re.IGNORECASE)),
    (
        "death",
        re.compile(
            r"\b("
            r"was slain by|drowned|blew up|hit the ground too hard|"
            r"tried to swim in lava|fell from a high place|was shot by|"
            r"went up in flames|was killed by"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    ("chat", re.compile(r"<(?P<player>[A-Za-z0-9_]{3,16})>")),
    (
        "login",
        re.compile(r"\b(UUID of player|logged in with entity id)\b", re.IGNORECASE),
    ),
    (
        "server",
        re.compile(
            r"\b(Starting minecraft server|Done \(|Stopping server|Saving players|Saving worlds)\b",
            re.IGNORECASE,
        ),
    ),
]

PLAYER_PATTERNS = [
    re.compile(
        r":\s(?P<player>[A-Za-z0-9_]{3,16}) joined the game",
        re.IGNORECASE,
    ),
    re.compile(
        r":\s(?P<player>[A-Za-z0-9_]{3,16}) left the game",
        re.IGNORECASE,
    ),
    re.compile(r"<(?P<player>[A-Za-z0-9_]{3,16})>"),
    re.compile(
        r":\s(?P<player>[A-Za-z0-9_]{3,16})\[/.*logged in with entity id",
        re.IGNORECASE,
    ),
]


def categorize_log_line(line: str) -> str:
    for category, pattern in CATEGORY_PATTERNS:
        if pattern.search(line):
            return category
    return "other"


def extract_player(line: str) -> str | None:
    for pattern in PLAYER_PATTERNS:
        match = pattern.search(line)
        if match:
            return match.group("player")
    return None


def build_labels(server: str, category: str, player: str | None) -> dict[str, str]:
    labels = {
        "job": JOB_NAME,
        "server": server,
        "category": category,
    }
    if player:
        labels["player"] = player
    return labels


def send_to_loki(server: str, message: str) -> None:
    category = categorize_log_line(message)
    player = extract_player(message)
    payload = {
        "streams": [
            {
                "stream": build_labels(server, category, player),
                "values": [[str(int(time.time() * 1e9)), message]],
            }
        ]
    }

    response = requests.post(LOKI_URL, json=payload, timeout=10)
    if response.status_code != 204:
        print(f"[{server}] Loki error {response.status_code}: {response.text}")


def monitor_log_file(server: str, file_path: str) -> None:
    last_inode = None
    last_size = None
    file = None

    while True:
        try:
            if not os.path.exists(file_path):
                if file and not file.closed:
                    file.close()
                file = None
                last_inode = None
                last_size = None
                print(f"[{server}] Missing file: {file_path}, waiting...")
                time.sleep(5)
                continue

            stat_result = os.stat(file_path)
            current_inode = stat_result.st_ino
            current_size = stat_result.st_size

            rotated_or_truncated = (
                file is None
                or file.closed
                or last_inode != current_inode
                or (last_size is not None and current_size < last_size)
            )

            if rotated_or_truncated:
                if file and not file.closed:
                    file.close()

                print(f"[{server}] Opening log: {file_path}")
                file = open(file_path, "r", encoding="utf-8", errors="replace")
                file.seek(0, os.SEEK_END)
                last_inode = current_inode

            line = file.readline()
            if line:
                send_to_loki(server, line.rstrip("\n"))
            else:
                time.sleep(0.5)

            last_size = current_size

        except Exception as error:
            print(f"[{server}] Error: {error}")
            if file and not file.closed:
                file.close()
            file = None
            last_inode = None
            last_size = None
            time.sleep(5)


def main() -> None:
    threads = []

    for server, path in LOG_SOURCES.items():
        thread = threading.Thread(
            target=monitor_log_file,
            args=(server, path),
            daemon=True,
        )
        thread.start()
        threads.append(thread)

    print("Monitoring Minecraft logs for:", ", ".join(LOG_SOURCES.keys()))

    for thread in threads:
        thread.join()


if __name__ == "__main__":
    main()
