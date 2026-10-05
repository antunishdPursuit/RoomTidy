"""Local metadata and explicit reference storage; no routine capture retention."""
from __future__ import annotations
import json
import math
import re
import sqlite3
import threading
import time
import uuid
from pathlib import Path


class Store:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self._lock = threading.RLock()
        self._open()

    def _open(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.references = self.data_dir / 'references'
        self.references.mkdir(exist_ok=True)
        self.db = sqlite3.connect(self.data_dir / 'roomtidy.sqlite3', check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS areas(id TEXT PRIMARY KEY,name TEXT NOT NULL,rect TEXT NOT NULL,
                preferences TEXT NOT NULL,reference TEXT NOT NULL,generation INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS episodes(area_id TEXT NOT NULL,mode TEXT NOT NULL,
                count INTEGER NOT NULL DEFAULT 0,alerted INTEGER NOT NULL DEFAULT 0,
                snooze_until REAL NOT NULL DEFAULT 0,PRIMARY KEY(area_id,mode));
            CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY,area_id TEXT,mode TEXT,
                status TEXT,evidence TEXT,observed_at REAL);
        ''')
        self.db.commit()

    @staticmethod
    def _mode(mode):
        if mode not in ('live', 'demo'):
            raise ValueError('Mode must be live or demo')
        return mode

    def get_setting(self, key, default=None):
        with self._lock:
            row = self.db.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
            return json.loads(row[0]) if row else default

    def set_setting(self, key, value):
        encoded = json.dumps(value, allow_nan=False)
        with self._lock, self.db:
            self.db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', (key, encoded))

    def areas(self, mode='live'):
        self._mode(mode)
        with self._lock:
            rows = self.db.execute('''SELECT a.*, COALESCE(e.count,0) count,
                COALESCE(e.alerted,0) alerted,COALESCE(e.snooze_until,0) snooze_until
                FROM areas a LEFT JOIN episodes e ON a.id=e.area_id AND e.mode=? ORDER BY a.rowid''', (mode,)).fetchall()
            result = []
            for row in rows:
                item = dict(row)
                item['rect'] = json.loads(item['rect'])
                item['alerted'] = bool(item['alerted'])
                item['reference_path'] = item['reference']
                result.append(item)
            return result

    def add_area(self, name, rect, preferences, reference):
        if not name.strip() or len(rect) != 4:
            raise ValueError('A name and normalized rectangle are required')
        x, y, w, h = rect
        if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in rect) or not (0 <= x < 1 and 0 <= y < 1 and w > 0 and h > 0 and x+w <= 1.000001 and y+h <= 1.000001):
            raise ValueError('Invalid normalized rectangle')
        if not isinstance(reference, bytes) or not reference:
            raise ValueError('Reference bytes are required')
        area_id = uuid.uuid4().hex
        with self._lock:
            path = self.references / (area_id + '.png')
            path.write_bytes(reference)
            try:
                with self.db:
                    self.db.execute('INSERT INTO areas VALUES (?,?,?,?,?,0)', (area_id, name.strip(), json.dumps(list(rect)), preferences, str(path)))
            except Exception:
                path.unlink(missing_ok=True)
                raise
        return area_id

    def reset_area(self, area_id):
        with self._lock, self.db:
            self.db.execute('UPDATE areas SET generation=generation+1 WHERE id=?', (area_id,))
            self.db.execute('DELETE FROM episodes WHERE area_id=?', (area_id,))

    def reset_episode(self, area_id, mode='live'):
        self._mode(mode)
        with self._lock, self.db:
            self.db.execute('UPDATE areas SET generation=generation+1 WHERE id=?', (area_id,))
            self.db.execute('DELETE FROM episodes WHERE area_id=? AND mode=?', (area_id, mode))

    def update_reference(self, area_id, png):
        if not isinstance(png, bytes) or not png:
            raise ValueError('Reference bytes are required')
        with self._lock:
            row = self.db.execute('SELECT reference FROM areas WHERE id=?', (area_id,)).fetchone()
            if row is None:
                raise KeyError(area_id)
            path = Path(row[0])
            temporary = path.with_suffix('.tmp')
            temporary.write_bytes(png)
            temporary.replace(path)
            self.reset_area(area_id)

    def update_preferences(self, area_id, preferences):
        with self._lock, self.db:
            self.db.execute('UPDATE areas SET preferences=? WHERE id=?', (preferences, area_id))
            self.reset_area(area_id)

    def observe(self, area_id, status, evidence, generation, mode, threshold, now=None):
        self._mode(mode)
        if status not in ('tidy', 'clutter_present', 'unable_to_assess'):
            raise ValueError('Invalid observation status')
        if isinstance(threshold, bool) or not isinstance(threshold, int) or threshold < 1:
            raise ValueError('Threshold must be a positive integer')
        now = time.time() if now is None else float(now)
        if not math.isfinite(now):
            raise ValueError('Invalid observation timestamp')
        with self._lock, self.db:
            area = self.db.execute('SELECT generation FROM areas WHERE id=?', (area_id,)).fetchone()
            if area is None or area[0] != generation:
                return False
            self.db.execute('INSERT OR IGNORE INTO episodes(area_id,mode) VALUES (?,?)', (area_id, mode))
            episode = self.db.execute('SELECT * FROM episodes WHERE area_id=? AND mode=?', (area_id, mode)).fetchone()
            count, alerted, snooze = episode['count'], episode['alerted'], episode['snooze_until']
            if status == 'tidy':
                count, alerted, snooze = 0, 0, 0
            elif status == 'clutter_present':
                count += 1
            due = status == 'clutter_present' and count >= threshold and not alerted and now >= snooze
            if due:
                alerted = 1
            self.db.execute('UPDATE episodes SET count=?,alerted=?,snooze_until=? WHERE area_id=? AND mode=?', (count, alerted, snooze, area_id, mode))
            self.db.execute('INSERT INTO history(area_id,mode,status,evidence,observed_at) VALUES (?,?,?,?,?)', (area_id, mode, status, str(evidence)[:1000], now))
            self.db.execute('DELETE FROM history WHERE id NOT IN (SELECT id FROM history ORDER BY id DESC LIMIT 500)')
            return bool(due)

    def snooze(self, area_id, seconds, mode='live', now=None):
        self._mode(mode)
        if not math.isfinite(seconds) or seconds < 0:
            raise ValueError('Invalid snooze duration')
        now = time.time() if now is None else float(now)
        with self._lock, self.db:
            if not self.db.execute('SELECT 1 FROM areas WHERE id=?', (area_id,)).fetchone():
                return
            self.db.execute('INSERT OR IGNORE INTO episodes(area_id,mode) VALUES (?,?)', (area_id, mode))
            self.db.execute('UPDATE episodes SET snooze_until=? WHERE area_id=? AND mode=?', (now + seconds, area_id, mode))

    def history(self, mode='live'):
        self._mode(mode)
        with self._lock:
            return [dict(row) for row in self.db.execute('SELECT * FROM history WHERE mode=? ORDER BY id DESC', (mode,))]

    def delete_data(self):
        with self._lock:
            # Generated reference names have exactly one lowercase UUID hex stem.
            # Include interrupted writes, but preserve unrelated directory content.
            paths = [path for path in self.references.iterdir()
                     if re.fullmatch(r'[0-9a-f]{32}\.(png|tmp)', path.name)
                     and (path.is_file() or path.is_symlink())]
            self.db.close()
            try:
                for path in paths:
                    path.unlink(missing_ok=True)
                for suffix in ('', '-wal', '-shm', '-journal'):
                    (self.data_dir / ('roomtidy.sqlite3' + suffix)).unlink(missing_ok=True)
            finally:
                # A locked file must not strand the application with a closed DB.
                # The original exception still reaches the caller to report partial deletion.
                self._open()

    def close(self):
        with self._lock:
            self.db.close()
