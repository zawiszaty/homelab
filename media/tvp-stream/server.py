from __future__ import annotations

import gzip
import io
import os
import re
import subprocess
import threading
import time
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from urllib.request import Request, urlopen


HOST = os.getenv("LISTEN_HOST", "0.0.0.0")
PORT = int(os.getenv("LISTEN_PORT", "8080"))
BASE_URL = os.getenv("TVP_STREAM_BASE_URL", "http://tvp-stream:8080").rstrip("/")
TVP1_URL = os.getenv("TVP1_URL", "https://vod.tvp.pl/live,1/tvp-1,399697")
TVP2_URL = os.getenv("TVP2_URL", "https://vod.tvp.pl/live,1/tvp-2,399698")
IPTV_ORG_URL = os.getenv("IPTV_ORG_URL", "https://iptv-org.github.io/iptv/languages/pol.m3u")
EPG_URL = os.getenv("EPG_URL", "https://epgshare01.online/epgshare01/epg_ripper_PL1.xml.gz")
STREAM_QUALITY = os.getenv("STREAM_QUALITY", "best")
STREAMLINK_BIN = os.getenv("STREAMLINK_BIN", "streamlink")
IPTV_CACHE_SECONDS = int(os.getenv("IPTV_CACHE_SECONDS", "900"))
EPG_CACHE_SECONDS = int(os.getenv("EPG_CACHE_SECONDS", "43200"))

IPTV_CHANNELS = {
    "polsat": ("Polsat.pl@SD", "Polsat"),
    "tv4": ("TV4.pl@SD", "TV4"),
    "tv-puls": ("TVPuls.pl@SD", "TV Puls"),
    "puls-2": ("Puls2.pl@SD", "Puls 2"),
}

EPG_CHANNEL_IDS = {
    "TVP.1.HD.pl": "TVP1.pl",
    "TVP.2.HD.pl": "TVP2.pl",
    "Polsat.HD.pl": "Polsat.pl@SD",
    "TV.4.HD.pl": "TV4.pl@SD",
    "TV.Puls.HD.pl": "TVPuls.pl@SD",
    "PULS.2.HD.pl": "Puls2.pl@SD",
}

_iptv_cache_lock = threading.Lock()
_iptv_cache_time = 0.0
_iptv_cache: dict[str, str] = {}
_epg_cache_lock = threading.Lock()
_epg_cache_time = 0.0
_epg_cache = b""


def parse_selected_channels(playlist: str) -> dict[str, str]:
    selected_by_id = {tvg_id: key for key, (tvg_id, _) in IPTV_CHANNELS.items()}
    result: dict[str, str] = {}
    pending_key: str | None = None

    for raw_line in playlist.splitlines():
        line = raw_line.strip()
        if line.startswith("#EXTINF:"):
            match = re.search(r'tvg-id="([^"]+)"', line)
            pending_key = selected_by_id.get(match.group(1)) if match else None
        elif line and not line.startswith("#"):
            if pending_key is not None:
                result[pending_key] = line
            pending_key = None

    return result


def get_iptv_channels() -> dict[str, str]:
    global _iptv_cache, _iptv_cache_time

    now = time.monotonic()
    if _iptv_cache and now - _iptv_cache_time < IPTV_CACHE_SECONDS:
        return _iptv_cache.copy()

    with _iptv_cache_lock:
        now = time.monotonic()
        if _iptv_cache and now - _iptv_cache_time < IPTV_CACHE_SECONDS:
            return _iptv_cache.copy()

        request = Request(IPTV_ORG_URL, headers={"User-Agent": "TVPStream/2.0"})
        try:
            with urlopen(request, timeout=15) as response:
                channels = parse_selected_channels(response.read().decode("utf-8"))
            if channels:
                _iptv_cache = channels
                _iptv_cache_time = now
        except OSError:
            if not _iptv_cache:
                raise

        return _iptv_cache.copy()


def filter_xmltv(compressed_guide: bytes) -> bytes:
    output = io.BytesIO()
    output.write(b'<?xml version="1.0" encoding="UTF-8"?>\n<tv generator-info-name="TVPStream">\n')

    with gzip.GzipFile(fileobj=io.BytesIO(compressed_guide)) as guide:
        for _, element in ET.iterparse(guide, events=("end",)):
            source_id = element.get("id") if element.tag == "channel" else element.get("channel")
            target_id = EPG_CHANNEL_IDS.get(source_id or "")
            if target_id is not None and element.tag in {"channel", "programme"}:
                if element.tag == "channel":
                    element.set("id", target_id)
                else:
                    element.set("channel", target_id)
                output.write(ET.tostring(element, encoding="utf-8"))
                output.write(b"\n")
            if element.tag in {"channel", "programme"}:
                element.clear()

    output.write(b"</tv>\n")
    return output.getvalue()


def get_epg() -> bytes:
    global _epg_cache, _epg_cache_time

    now = time.monotonic()
    if _epg_cache and now - _epg_cache_time < EPG_CACHE_SECONDS:
        return _epg_cache

    with _epg_cache_lock:
        now = time.monotonic()
        if _epg_cache and now - _epg_cache_time < EPG_CACHE_SECONDS:
            return _epg_cache

        request = Request(EPG_URL, headers={"User-Agent": "TVPStream/2.0"})
        try:
            with urlopen(request, timeout=60) as response:
                guide = filter_xmltv(response.read())
            if guide:
                _epg_cache = guide
                _epg_cache_time = now
        except (OSError, EOFError, ET.ParseError):
            if not _epg_cache:
                raise

        return _epg_cache

class Handler(BaseHTTPRequestHandler):
    server_version = "TVPStream/2.0"

    def do_HEAD(self) -> None:
        path = urlparse(self.path).path
        if path == "/healthz":
            self._headers(200, "text/plain; charset=utf-8", 0)
        elif path == "/playlist.m3u":
            body = self._playlist()
            self._headers(200, "audio/x-mpegurl; charset=utf-8", len(body))
        elif path == "/guide.xml":
            try:
                body = get_epg()
            except (OSError, EOFError, ET.ParseError):
                self._headers(502, "text/plain; charset=utf-8", 0)
            else:
                self._headers(200, "application/xml; charset=utf-8", len(body))
        elif path in {"/stream/tvp1", "/stream/tvp2"} or path.removeprefix("/stream/") in IPTV_CHANNELS:
            self._headers(200, "video/mp2t")
        else:
            self._headers(404, "text/plain; charset=utf-8", 0)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/healthz":
            self._send(200, b"ok\n", "text/plain; charset=utf-8")
        elif path == "/playlist.m3u":
            self._send(200, self._playlist(), "audio/x-mpegurl; charset=utf-8")
        elif path == "/guide.xml":
            try:
                guide = get_epg()
            except (OSError, EOFError, ET.ParseError):
                self._send(502, b"EPG source is unavailable\n", "text/plain; charset=utf-8")
            else:
                self._send(200, guide, "application/xml; charset=utf-8")
        elif path == "/stream/tvp1":
            self._stream(TVP1_URL, "TVP 1")
        elif path == "/stream/tvp2":
            self._stream(TVP2_URL, "TVP 2")
        elif (channel_key := path.removeprefix("/stream/")) in IPTV_CHANNELS:
            try:
                source_url = get_iptv_channels().get(channel_key)
            except OSError:
                source_url = None
            if source_url is None:
                self._send(502, b"IPTV source is unavailable\n", "text/plain; charset=utf-8")
            else:
                self._stream(source_url, IPTV_CHANNELS[channel_key][1])
        else:
            self._send(404, b"not found\n", "text/plain; charset=utf-8")

    def _playlist(self) -> bytes:
        lines = [
            "#EXTM3U",
            '#EXTINF:-1 tvg-id="TVP1.pl" tvg-name="TVP 1" group-title="TVP",TVP 1',
            f"{BASE_URL}/stream/tvp1",
            '#EXTINF:-1 tvg-id="TVP2.pl" tvg-name="TVP 2" group-title="TVP",TVP 2',
            f"{BASE_URL}/stream/tvp2",
        ]
        try:
            available_channels = get_iptv_channels()
        except OSError:
            available_channels = {}

        for key, (tvg_id, name) in IPTV_CHANNELS.items():
            if key not in available_channels:
                continue
            lines.extend(
                [
                    f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{name}" group-title="Polska",{name}',
                    f"{BASE_URL}/stream/{key}",
                ]
            )

        return ("\n".join(lines) + "\n").encode()

    def _stream(self, source_url: str, channel_name: str) -> None:
        command = [
            STREAMLINK_BIN,
            "--stdout",
            "--loglevel",
            "error",
            "--stream-timeout",
            "30",
            "--ffmpeg-copyts",
            "--ffmpeg-start-at-zero",
            source_url,
            STREAM_QUALITY,
        ]
        process: subprocess.Popen[bytes] | None = None
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            assert process.stdout is not None
            first_chunk = process.stdout.read(64 * 1024)
            if not first_chunk:
                process.wait(timeout=5)
                self._send(502, f"{channel_name} stream is unavailable\n".encode(), "text/plain; charset=utf-8")
                return

            self._headers(200, "video/mp2t")
            self.wfile.write(first_chunk)
            while chunk := process.stdout.read(64 * 1024):
                self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except (OSError, subprocess.SubprocessError):
            if not self.wfile.closed:
                try:
                    self._send(502, f"Unable to start {channel_name} stream\n".encode(), "text/plain; charset=utf-8")
                except (BrokenPipeError, ConnectionResetError):
                    pass
        finally:
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self._headers(status, content_type, len(body))
        if self.command != "HEAD":
            self.wfile.write(body)

    def _headers(self, status: int, content_type: str, content_length: int | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        if content_length is not None:
            self.send_header("Content-Length", str(content_length))
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.client_address[0]} - {format % args}", flush=True)


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"TVP Stream listening on {HOST}:{PORT}", flush=True)
    server.serve_forever()
