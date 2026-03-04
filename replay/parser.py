"""
Local Rocket League replay parser - no Ballchasing required.

Uses rattletrap (bundled or in PATH) to decode .replay to JSON,
then extracts player stats. Optionally uses carball if available for richer stats.
"""
import hashlib
import json
import os
import platform
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

_REPLAY_DIR = Path(__file__).parent.parent
_RATTLETRAP_DIR = _REPLAY_DIR / "bin" / "rattletrap"
_RATTLETRAP_URLS = {
    "Windows": "https://github.com/tfausak/rattletrap/releases/download/14.1.4/rattletrap-14.1.4-win32-x64.tar.gz",
    "Linux": "https://github.com/tfausak/rattletrap/releases/download/14.1.4/rattletrap-14.1.4-linux-x64.tar.gz",
    "Darwin": "https://github.com/tfausak/rattletrap/releases/download/14.1.4/rattletrap-14.1.4-darwin-arm64.tar.gz" if platform.machine() == "arm64" else "https://github.com/tfausak/rattletrap/releases/download/14.1.4/rattletrap-14.1.4-darwin-x64.tar.gz",
}


def _get_rattletrap_path() -> Optional[Path]:
    """Get path to rattletrap binary."""
    if shutil.which("rattletrap"):
        return Path(shutil.which("rattletrap"))

    system = platform.system()
    if system == "Windows":
        exe = _RATTLETRAP_DIR / "rattletrap.exe"
    else:
        exe = _RATTLETRAP_DIR / "rattletrap"
    if exe.exists():
        if system != "Windows":
            os.chmod(exe, exe.stat().st_mode | stat.S_IXUSR)
        return exe
    return None


def _ensure_rattletrap() -> Optional[Path]:
    """Ensure rattletrap is available. Downloads if missing."""
    if _get_rattletrap_path():
        return _get_rattletrap_path()

    try:
        import urllib.request
        import tarfile

        system = platform.system()
        url = _RATTLETRAP_URLS.get(system)
        if not url:
            return None

        _RATTLETRAP_DIR.mkdir(parents=True, exist_ok=True)
        arc_path = _RATTLETRAP_DIR / "rattletrap.tar.gz"
        urllib.request.urlretrieve(url, arc_path)

        with tarfile.open(arc_path, "r:gz") as tf:
            tf.extractall(_RATTLETRAP_DIR)

        # Find exe (may be in subdir like rattletrap-14.1.4-win32-x64/)
        for p in _RATTLETRAP_DIR.rglob("rattletrap*"):
            if p.is_file() and (p.name == "rattletrap" or p.name == "rattletrap.exe"):
                target = _RATTLETRAP_DIR / p.name
                if p.resolve() != target.resolve():
                    shutil.move(str(p), str(target))
                break

        arc_path.unlink(missing_ok=True)
        return _get_rattletrap_path()
    except Exception:
        return None


def _decode_with_rattletrap(replay_path: Path, fast: bool = False) -> Optional[dict]:
    """Run rattletrap to decode replay to JSON. fast=True uses --fast (header only, works for newer replays)."""
    rt = _ensure_rattletrap()
    if not rt:
        return None

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as out:
        out_path = Path(out.name)
    try:
        args = [str(rt), "-i", str(replay_path), "-o", str(out_path), "-c"]
        if fast:
            args.append("-f")  # --fast: header only, avoids ViralItemActor etc in newer RL
        subprocess.run(
            args,
            capture_output=True,
            timeout=120,
            check=True,
        )
        with open(out_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None
    finally:
        out_path.unlink(missing_ok=True)


def _find_property(obj, *names) -> Optional[any]:
    """Recursively find first property matching any of names in nested dict/list."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in names:
                return v
            r = _find_property(v, *names)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _find_property(v, *names)
            if r is not None:
                return r
    return None


def _extract_properties(obj: dict, keys: list[str]) -> dict:
    """Extract dict of key->value from object that may have 'value' or direct props."""
    out = {}
    if isinstance(obj, dict):
        for k in keys:
            if k in obj:
                v = obj[k]
                if isinstance(v, dict) and "value" in v:
                    out[k] = v["value"]
                else:
                    out[k] = v
    return out


def _extract_unique_id(unique_id_prop: dict) -> tuple[str, str]:
    """
    Extract platform and platform_id from rattletrap UniqueId structure.
    Returns (platform, platform_id) e.g. ('steam', '76561198123456789') or ('', '').
    """
    if not unique_id_prop or not isinstance(unique_id_prop, dict):
        return ("", "")
    val = unique_id_prop.get("value")
    if not isinstance(val, dict):
        return ("", "")
    # Rattletrap: UniqueId can be {value: {struct: {fields: {elements: [[name, val], ...]}}}}
    struct = val.get("struct", {}) if isinstance(val, dict) else {}
    fields = struct.get("fields", {}) if isinstance(struct, dict) else {}
    elements = fields.get("elements", []) if isinstance(fields, dict) else []
    field_map = {}
    for item in elements:
        if isinstance(item, list) and len(item) >= 2:
            field_map[item[0]] = item[1]
    # Common keys: SystemId (0=Steam, 1=PS3, 2=PS4, 3=Xbox, 4=Switch, 5=Epic), RemoteId/OnlineId
    sys_id = _prop_val(field_map.get("SystemId", {}))
    remote = _prop_val(field_map.get("RemoteId", {})) or _prop_val(field_map.get("OnlineId", {}))
    if remote is None and isinstance(field_map.get("RemoteId"), dict):
        rv = field_map["RemoteId"].get("value")
        if isinstance(rv, dict) and "str" in rv:
            remote = rv.get("str")
        elif isinstance(rv, dict) and "q_word" in rv:
            remote = str(rv.get("q_word", ""))
    platform = ""
    if sys_id is not None:
        sys_map = {0: "steam", 1: "ps3", 2: "ps4", 3: "xbox", 5: "epic"}
        platform = sys_map.get(int(sys_id), "")
    platform_id = str(remote) if remote is not None else ""
    return (platform, platform_id)


def _prop_val(prop: dict) -> any:
    """Extract value from rattletrap property dict: {value: {int: 5}} or {value: {str: 'x'}}."""
    v = prop.get("value") if isinstance(prop, dict) else None
    if not isinstance(v, dict):
        return v
    for key in ("int", "str", "float", "bool", "q_word"):
        if key in v:
            val = v[key]
            if key == "bool":
                return bool(val)
            if key == "float":
                return float(val) if val is not None else None
            if key in ("int", "q_word"):
                return int(val) if val is not None else None
            return val
    return None


def _parse_rattletrap_header(data: dict) -> tuple[dict, list[dict]]:
    """
    Parse rattletrap --fast output. Header has PlayerStats with full stats.
    Returns (metadata, players).
    """
    meta = {"title": "", "map_code": "", "team_size": 3, "duration": 0, "overtime": False}
    players = []

    header = data.get("header") or data
    body = header.get("body") or header
    props = body.get("properties") or {}
    elements = props.get("elements") or []

    # elements: [[prop_name, prop_dict], ...]
    prop_map = {}
    for item in elements:
        if isinstance(item, list) and len(item) >= 2:
            prop_map[item[0]] = item[1]

    meta["team_size"] = _prop_val(prop_map.get("TeamSize", {})) or 3
    meta["duration"] = int(_prop_val(prop_map.get("TotalSecondsPlayed", {})) or 0)

    # PlayerStats array
    ps_prop = prop_map.get("PlayerStats", {})
    ps_val = ps_prop.get("value") if isinstance(ps_prop, dict) else None
    arr = ps_val.get("array") if isinstance(ps_val, dict) else []
    if not isinstance(arr, list):
        return meta, players

    for struct in arr:
        if isinstance(struct, dict) and "struct" in struct:
            fields = struct["struct"].get("fields", {}).get("elements") or []
        else:
            fields = struct.get("elements") or []
        field_map = {}
        for f in fields:
            if isinstance(f, list) and len(f) >= 2:
                field_map[f[0]] = f[1]

        name = _prop_val(field_map.get("Name", {}))
        if not name or isinstance(name, int):
            continue
        team_idx = _prop_val(field_map.get("Team", {})) or 0
        if isinstance(team_idx, dict):
            team_idx = team_idx.get("int", 0)
        team_color = "blue" if team_idx == 0 else "orange"

        platform, platform_id = _extract_unique_id(field_map.get("UniqueId", {}))

        goals = _prop_val(field_map.get("Goals", {})) or 0
        assists = _prop_val(field_map.get("Assists", {})) or 0
        saves = _prop_val(field_map.get("Saves", {})) or 0
        shots = _prop_val(field_map.get("Shots", {})) or 0
        score = _prop_val(field_map.get("Score", {})) or 0

        shot_pct = (100 * goals / shots) if shots else None
        players.append({
            "name": str(name),
            "platform": platform or "",
            "platform_id": platform_id or "",
            "team": team_color,
            "team_color": team_color,
            "goals": int(goals) if goals is not None else 0,
            "assists": int(assists) if assists is not None else 0,
            "saves": int(saves) if saves is not None else 0,
            "shots": int(shots) if shots is not None else 0,
            "shots_against": 0,
            "shooting_percentage": round(shot_pct, 1) if shot_pct is not None else None,
            "score": int(score) if score is not None else 0,
            "mvp": False,
            "amount_collected": None, "bpm": None, "bcpm": None, "amount_collected_big": None,
            "amount_collected_small": None, "amount_stolen": None, "amount_used_while_supersonic": None,
            "percent_zero_boost": None, "percent_full_boost": None, "avg_amount": None,
            "avg_speed": None, "total_distance": None, "percent_supersonic_speed": None,
            "percent_boost_speed": None, "percent_slow_speed": None, "percent_ground": None,
            "percent_low_air": None, "percent_high_air": None, "count_powerslide": None,
            "avg_powerslide_duration": None, "percent_defensive_third": None,
            "percent_offensive_third": None, "percent_neutral_third": None,
            "percent_behind_ball": None, "percent_infront_ball": None,
            "avg_distance_to_ball": None, "avg_distance_to_mates": None,
            "demos_inflicted": 0, "demos_taken": 0,
        })

    return meta, players


def _get_val(obj, *keys) -> any:
    """Get value from obj; handle {value: X} wrapper."""
    for k in keys:
        v = obj.get(k) if isinstance(obj, dict) else None
        if v is not None:
            return v.get("value", v) if isinstance(v, dict) and "value" in v else v
    return None


def _parse_rattletrap_json(data: dict) -> tuple[dict, list[dict]]:
    """
    Extract replay metadata and player stats from rattletrap JSON.
    Returns (metadata, players).
    """
    meta = {"title": "", "map_code": "", "team_size": 3, "duration": 0, "overtime": False}
    players = []
    seen_names = set()

    # Rattletrap: nested structure - body/content/frames or similar
    def find_frames(obj, depth=0):
        if depth > 20:
            return []
        if isinstance(obj, dict):
            if "frames" in obj:
                return obj["frames"] if isinstance(obj["frames"], list) else []
            if "keyframes" in obj:
                return obj["keyframes"] if isinstance(obj["keyframes"], list) else []
            for v in obj.values():
                r = find_frames(v, depth + 1)
                if r:
                    return r
        elif isinstance(obj, list):
            for v in obj:
                r = find_frames(v, depth + 1)
                if r:
                    return r
        return []

    def scan_for_pris(obj, depth=0):
        if depth > 25:
            return
        if isinstance(obj, dict):
            name = _get_val(obj, "PlayerName", "playerName")
            if isinstance(name, str) and name and name not in seen_names:
                goals = _get_val(obj, "Goals", "goals")
                assists = _get_val(obj, "Assists", "assists")
                saves = _get_val(obj, "Saves", "saves")
                shots = _get_val(obj, "Shots", "shots")
                score = _get_val(obj, "Score", "score")
                team_idx = _get_val(obj, "TeamIndex", "teamIndex")
                is_bot = _get_val(obj, "bBot", "bBot")
                if is_bot:
                    return
                seen_names.add(name)
                try:
                    goals = int(goals) if goals is not None else 0
                    assists = int(assists) if assists is not None else 0
                    saves = int(saves) if saves is not None else 0
                    shots = int(shots) if shots is not None else 0
                    score = int(score) if score is not None else 0
                    team_idx = int(team_idx) if team_idx is not None else 0
                except (TypeError, ValueError):
                    goals = assists = saves = shots = score = 0
                    team_idx = 0
                shot_pct = (100 * goals / shots) if shots else None
                players.append({
                    "name": name, "platform": "", "platform_id": "",
                    "team": "blue" if team_idx == 0 else "orange",
                    "team_color": "blue" if team_idx == 0 else "orange",
                    "goals": goals, "assists": assists, "saves": saves, "shots": shots,
                    "shots_against": 0, "shooting_percentage": shot_pct, "score": score, "mvp": False,
                    "amount_collected": None, "bpm": None, "bcpm": None, "amount_collected_big": None,
                    "amount_collected_small": None, "amount_stolen": None, "amount_used_while_supersonic": None,
                    "percent_zero_boost": None, "percent_full_boost": None, "avg_amount": None,
                    "avg_speed": None, "total_distance": None, "percent_supersonic_speed": None,
                    "percent_boost_speed": None, "percent_slow_speed": None, "percent_ground": None,
                    "percent_low_air": None, "percent_high_air": None, "count_powerslide": None,
                    "avg_powerslide_duration": None, "percent_defensive_third": None,
                    "percent_offensive_third": None, "percent_neutral_third": None,
                    "percent_behind_ball": None, "percent_infront_ball": None,
                    "avg_distance_to_ball": None, "avg_distance_to_mates": None,
                    "demos_inflicted": 0, "demos_taken": 0,
                })
            for v in obj.values():
                scan_for_pris(v, depth + 1)
        elif isinstance(obj, list):
            for v in obj:
                scan_for_pris(v, depth + 1)

    frames = find_frames(data)
    if frames:
        scan_for_pris(frames[-1])
    if not players:
        scan_for_pris(data)

    # Metadata from header
    header = data.get("header") or data.get("replayHeader") or data
    props = header.get("properties") or header.get("propertiesValue") or []
    if isinstance(props, dict):
        props = [{"name": k, "value": v} for k, v in props.items()]
    for p in props if isinstance(props, list) else []:
        name = p.get("name") if isinstance(p, dict) else None
        val = p.get("value") if isinstance(p, dict) else p
        if isinstance(val, dict) and "value" in val:
            val = val["value"]
        if name == "MapName":
            meta["map_code"] = str(val) if val else ""
        elif name == "ReplayName":
            meta["title"] = str(val) if val else ""
        elif name == "TeamSize":
            meta["team_size"] = int(val) if val is not None else 3
        elif name == "bOverTime":
            meta["overtime"] = bool(val) if val is not None else False

    # Duration from frames (30 fps typically)
    if frames and isinstance(frames, list):
        meta["duration"] = len(frames) // 30  # Approx seconds

    return meta, players


def parse_replay_bytes(data: bytes) -> Optional[tuple[dict, list[dict]]]:
    """
    Parse .replay file bytes. Returns (metadata, players) or None.
    metadata: title, map_code, team_size, duration, overtime
    players: list of dicts matching our schema (goals, assists, etc.)
    """
    # Try carball first (richer stats) if available
    try:
        import carball  # type: ignore
        with tempfile.NamedTemporaryFile(suffix=".replay", delete=False) as f:
            f.write(data)
            path = Path(f.name)
        try:
            am = carball.analyze_replay_file(str(path), calculate_intensive_events=False)
            json_data = am.get_json_data()
            proto = am.get_protobuf_data()
            meta = {
                "title": getattr(proto, "name", None) or "",
                "map_code": getattr(proto, "map", None) or "",
                "team_size": len(getattr(proto, "players", [])) // 2 or 3,
                "duration": int(getattr(proto, "game", None).length_seconds or 0) if hasattr(proto, "game") and proto.HasField("game") else 0,
                "overtime": getattr(getattr(proto, "game", None), "overtime", False) or False,
            }
            players = []
            for p in getattr(proto, "players", []):
                stats = getattr(p, "stats", None)
                name = getattr(p, "name", None) or ""
                team = 0 if "blue" in str(getattr(p, "team", "")).lower() else 1
                team_color = "blue" if team == 0 else "orange"
                if stats:
                    boost = getattr(stats, "boost", None)
                    core = getattr(stats, "core", None)
                    movement = getattr(stats, "movement", None)
                    positioning = getattr(stats, "positioning", None)
                    demo = getattr(stats, "demo", None)
                    players.append({
                        "name": name,
                        "platform": "",
                        "platform_id": "",
                        "team": team_color,
                        "team_color": team_color,
                        "goals": getattr(core, "goals", 0) if core else 0,
                        "assists": getattr(core, "assists", 0) if core else 0,
                        "saves": getattr(core, "saves", 0) if core else 0,
                        "shots": getattr(core, "shots", 0) if core else 0,
                        "shots_against": getattr(core, "shots_against", 0) if core else 0,
                        "shooting_percentage": getattr(core, "shooting_percentage", None) if core else None,
                        "score": getattr(core, "score", 0) if core else 0,
                        "mvp": getattr(core, "mvp", False) if core else False,
                        "amount_collected": getattr(boost, "amount_collected", None) if boost else None,
                        "bpm": getattr(boost, "bpm", None) if boost else None,
                        "bcpm": getattr(boost, "bcpm", None) if boost else None,
                        "amount_collected_big": getattr(boost, "amount_collected_big", None) if boost else None,
                        "amount_collected_small": getattr(boost, "amount_collected_small", None) if boost else None,
                        "amount_stolen": getattr(boost, "amount_stolen", None) if boost else None,
                        "amount_used_while_supersonic": getattr(boost, "amount_used_while_supersonic", None) if boost else None,
                        "percent_zero_boost": getattr(boost, "percent_zero_boost", None) if boost else None,
                        "percent_full_boost": getattr(boost, "percent_full_boost", None) if boost else None,
                        "avg_amount": getattr(boost, "avg_amount", None) if boost else None,
                        "avg_speed": getattr(movement, "avg_speed", None) if movement else None,
                        "total_distance": getattr(movement, "total_distance", None) if movement else None,
                        "percent_supersonic_speed": getattr(movement, "percent_supersonic_speed", None) if movement else None,
                        "percent_boost_speed": getattr(movement, "percent_boost_speed", None) if movement else None,
                        "percent_slow_speed": getattr(movement, "percent_slow_speed", None) if movement else None,
                        "percent_ground": getattr(movement, "percent_ground", None) if movement else None,
                        "percent_low_air": getattr(movement, "percent_low_air", None) if movement else None,
                        "percent_high_air": getattr(movement, "percent_high_air", None) if movement else None,
                        "count_powerslide": getattr(movement, "count_powerslide", None) if movement else None,
                        "avg_powerslide_duration": getattr(movement, "avg_powerslide_duration", None) if movement else None,
                        "percent_defensive_third": getattr(positioning, "percent_defensive_third", None) if positioning else None,
                        "percent_offensive_third": getattr(positioning, "percent_offensive_third", None) if positioning else None,
                        "percent_neutral_third": getattr(positioning, "percent_neutral_third", None) if positioning else None,
                        "percent_behind_ball": getattr(positioning, "percent_behind_ball", None) if positioning else None,
                        "percent_infront_ball": getattr(positioning, "percent_infront_ball", None) if positioning else None,
                        "avg_distance_to_ball": getattr(positioning, "avg_distance_to_ball", None) if positioning else None,
                        "avg_distance_to_mates": getattr(positioning, "avg_distance_to_mates", None) if positioning else None,
                        "demos_inflicted": getattr(demo, "inflicted", 0) if demo else 0,
                        "demos_taken": getattr(demo, "taken", 0) if demo else 0,
                    })
                else:
                    players.append({
                        "name": name, "platform": "", "platform_id": "",
                        "team": team_color, "team_color": team_color,
                        "goals": 0, "assists": 0, "saves": 0, "shots": 0,
                        "shots_against": 0, "shooting_percentage": None, "score": 0, "mvp": False,
                        **{k: None for k in ["amount_collected", "bpm", "bcpm", "amount_collected_big", "amount_collected_small",
                            "amount_stolen", "amount_used_while_supersonic", "percent_zero_boost", "percent_full_boost", "avg_amount",
                            "avg_speed", "total_distance", "percent_supersonic_speed", "percent_boost_speed", "percent_slow_speed",
                            "percent_ground", "percent_low_air", "percent_high_air", "count_powerslide", "avg_powerslide_duration",
                            "percent_defensive_third", "percent_offensive_third", "percent_neutral_third",
                            "percent_behind_ball", "percent_infront_ball", "avg_distance_to_ball", "avg_distance_to_mates"]},
                        "demos_inflicted": 0, "demos_taken": 0,
                    })
            return (meta, players) if players else None
        finally:
            path.unlink(missing_ok=True)
    except ImportError:
        pass

    # Fallback: rattletrap (try full decode first, then --fast for newer replays)
    with tempfile.NamedTemporaryFile(suffix=".replay", delete=False) as f:
        f.write(data)
        path = Path(f.name)
    try:
        json_data = _decode_with_rattletrap(path, fast=False)
        if json_data:
            meta, players = _parse_rattletrap_json(json_data)
            if players:
                return (meta, players)
        # Newer RL replays may have unknown classes (ViralItemActor); use header-only
        json_data = _decode_with_rattletrap(path, fast=True)
        if json_data:
            meta, players = _parse_rattletrap_header(json_data)
            if players:
                return (meta, players)
        return None
    finally:
        path.unlink(missing_ok=True)


def replay_id_from_bytes(data: bytes) -> str:
    """Generate unique replay ID (for storage) from file bytes."""
    h = hashlib.sha256(data).hexdigest()[:16]
    return f"local-{h}"
