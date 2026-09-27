"""Small, file-versioned read models; original analysis artifacts remain authoritative."""

from collections import OrderedDict
import hashlib
import json
import logging
import os
from pathlib import Path
import tempfile
from threading import RLock

logger = logging.getLogger(__name__)
VERSION = 7


def signature(path):
    stat = path.stat()
    status_path = cancellation_path(path)
    status = status_path.stat() if status_path.exists() else None
    return [stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size,
            [status.st_mtime_ns, status.st_size] if status else None]


def cancellation_path(path):
    return path.parent / ".portfolio-status" / path.name


def cancellation_view(path, payload):
    status_path = cancellation_path(path)
    if not status_path.exists():
        return payload
    status = json.loads(status_path.read_text())
    if status.get("run_id") != path.name or status.get("pipeline_status") not in {"cancelling", "cancelled"}:
        raise ValueError("Invalid saved cancellation state")
    return {**payload, "pipeline_status": status["pipeline_status"], "cancellation": status}


def memo_etag(path):
    value = json.dumps([VERSION, str(path.resolve()), signature(path)])
    return 'W/"' + hashlib.sha256(value.encode()).hexdigest() + '"'


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_cache(path, value):
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, ensure_ascii=False, separators=(",", ":"))
        os.replace(temporary, path)
    except OSError:
        # A read-only/full disk must not prevent reading the original memo.
        logger.warning("Unable to persist portfolio read cache: %s", path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


class PortfolioReadStore:
    def __init__(self):
        self._indexes = {}
        self._memos = OrderedDict()
        self._index_lock = RLock()
        self._memo_lock = RLock()

    @staticmethod
    def _memo_path(path):
        return path.parent / f".portfolio-views-v{VERSION}" / (path.name + ".json")

    def _remember_memo(self, path, stamp, memo):
        with self._memo_lock:
            key = str(path.resolve())
            self._memos[key] = {"signature": stamp, "memo": memo}
            self._memos.move_to_end(key)
            while len(self._memos) > 64:
                self._memos.popitem(last=False)

    def forget(self, path):
        root = path.parent.resolve()
        with self._index_lock:
            with self._memo_lock:
                self._memos.pop(str(path.resolve()), None)
            try:
                self._memo_path(path).unlink(missing_ok=True)
            except OSError:
                logger.warning("Unable to remove obsolete portfolio read cache: %s", path)
            index_path = root / f".portfolio-index-v{VERSION}.json"
            index = self._indexes.get(root)
            if index is None:
                try:
                    index = _read_json(index_path)
                except (OSError, ValueError):
                    index = {}
            if isinstance(index, dict) and path.name in index:
                index.pop(path.name)
                self._indexes[root] = index
                _write_cache(index_path, index)

    def memo(self, path, build):
        stamp = signature(path)
        key = str(path.resolve())
        with self._memo_lock:
            cached = self._memos.get(key)
            if cached and cached["signature"] == stamp:
                self._memos.move_to_end(key)
                return cached["memo"]
        try:
            cached = _read_json(self._memo_path(path))
        except (OSError, ValueError):
            cached = {}
        if not isinstance(cached, dict):
            cached = {}
        if cached.get("signature") == stamp and isinstance(cached.get("memo"), dict):
            memo = cached["memo"]
        else:
            memo = build(path, _read_json(path))["memo"]
            if signature(path) == stamp:
                _write_cache(self._memo_path(path), {"signature": stamp, "memo": memo})
        if signature(path) == stamp:
            self._remember_memo(path, stamp, memo)
        return memo

    def list(self, roots, limit, build):
        # Cold indexing is single-flight, but never holds up direct memo reads.
        with self._index_lock:
            rows = {}
            for root in roots:
                root = root.resolve()
                if not root.is_dir():
                    continue
                index_path = root / f".portfolio-index-v{VERSION}.json"
                if root not in self._indexes:
                    try:
                        saved = _read_json(index_path)
                        self._indexes[root] = saved if isinstance(saved, dict) else {}
                    except (OSError, ValueError):
                        self._indexes[root] = {}
                index = self._indexes[root]
                current = {}
                for path in root.glob("*.json"):
                    if path.name.startswith(".") or path.name.endswith(".checkpoint.json") or not path.is_file():
                        continue
                    try:
                        stamp = signature(path)
                        entry = index.get(path.name)
                        if (not isinstance(entry, dict) or entry.get("signature") != stamp
                                or (entry.get("summary") is not None and not isinstance(entry["summary"], dict))):
                            result = build(path, _read_json(path))
                            if signature(path) != stamp:
                                continue  # A run was updated while being read; retry next time.
                            entry = {"signature": stamp, "summary": result["summary"] if result else None}
                            if result:
                                self._remember_memo(path, stamp, result["memo"])
                                _write_cache(self._memo_path(path), {"signature": stamp, "memo": result["memo"]})
                        current[path.name] = entry
                        if entry.get("summary"):
                            rows[str(path.resolve())] = (stamp[0], entry["summary"])
                    except (OSError, ValueError, TypeError):
                        logger.warning("Unable to index portfolio artifact: %s", path)
                if current != index:
                    for name in index.keys() - current.keys():
                        if Path(name).name != name:
                            continue
                        path = root / name
                        with self._memo_lock:
                            self._memos.pop(str(path.resolve()), None)
                        try:
                            self._memo_path(path).unlink(missing_ok=True)
                        except OSError:
                            logger.warning("Unable to remove obsolete portfolio read cache: %s", path)
                    self._indexes[root] = current
                    _write_cache(index_path, current)
            return [row for _, row in sorted(rows.values(), key=lambda item: item[0], reverse=True)[:limit]]


portfolio_read_store = PortfolioReadStore()
