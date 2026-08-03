"""Database-backed emotion history and statistics handlers for Resona."""

import json
import os
from collections import defaultdict
from datetime import datetime, timedelta

import pymysql
from aiohttp import web


EMOTIONS = ("happy", "sad", "neutral", "anger")
AGGREGATE_FORMATS = {
    "hour": "%Y-%m-%d %H:00",
    "day": "%Y-%m-%d",
    "week": "%Y-%m-%d",
    "month": "%Y-%m",
}


def _cors(response):
    response.headers.update({
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "client-id, content-type, device-id, Authorization",
        "Access-Control-Allow-Credentials": "true",
    })
    return response


def _db():
    return pymysql.connect(
        host="127.0.0.1",
        user=os.environ.get("RESONA_DB_USER", "resona"),
        password=os.environ["RESONA_DB_PASSWORD"],
        database=os.environ.get("RESONA_DB_NAME", "xiaozhi_esp32_server"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=3,
    )


def _parse_date(value, name):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"{name} must use YYYY-MM-DD") from exc


def _filters(query):
    clauses = []
    params = []
    device_id = (query.get("device_id") or query.get("deviceId") or "").strip()
    start = _parse_date(query.get("start"), "start")
    end = _parse_date(query.get("end"), "end")
    if start and end and start > end:
        raise ValueError("start must not be later than end")
    if device_id:
        clauses.append("device_id = %s")
        params.append(device_id)
    if start:
        clauses.append("timestamp >= %s")
        params.append(start)
    if end:
        clauses.append("timestamp < %s")
        params.append(end + timedelta(days=1))
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", params


def _safe_belief(raw):
    if isinstance(raw, list):
        values = raw
    else:
        try:
            values = json.loads(raw or "[]")
        except (TypeError, ValueError):
            values = []
    values = values if isinstance(values, list) else []
    return [float(v) for v in values[:4]]


def _period(timestamp, aggregate):
    if aggregate == "month":
        return timestamp.strftime(AGGREGATE_FORMATS[aggregate])
    if aggregate == "week":
        timestamp = timestamp - timedelta(days=timestamp.weekday())
    return timestamp.strftime(AGGREGATE_FORMATS[aggregate])


def _trend(rows, aggregate):
    buckets = defaultdict(lambda: {emotion: 0 for emotion in EMOTIONS})
    totals = defaultdict(int)
    for row in rows:
        dominant = row.get("dominant")
        timestamp = row.get("timestamp")
        if dominant not in EMOTIONS or not isinstance(timestamp, datetime):
            continue
        label = _period(timestamp, aggregate)
        buckets[label][dominant] += 1
        totals[label] += 1

    labels = sorted(buckets)
    result = {"labels": labels}
    for emotion in EMOTIONS:
        result[emotion] = [
            round(buckets[label][emotion] * 100 / totals[label], 1) if totals[label] else 0
            for label in labels
        ]
    return result


def _summary(rows):
    counts = defaultdict(int)
    conflict_total = 0.0
    high_conflict_count = 0
    for row in rows:
        dominant = row.get("dominant")
        if dominant:
            counts[dominant] += 1
        conflict_total += float(row.get("conflict") or 0)
        high_conflict_count += 1 if row.get("high_conflict") else 0
    dominant_top = max(counts, key=counts.get) if counts else "--"
    return {
        "total": len(rows),
        "dominantTop": dominant_top,
        "avgK": round(conflict_total / len(rows), 4) if rows else 0,
        "highConflictCount": high_conflict_count,
    }


def _load_rows(query):
    where, params = _filters(query)
    sql = (
        "SELECT id, device_id, timestamp, dominant, score, belief_json, conflict, "
        "high_conflict, snr, lux, vision_reliability, audio_reliability "
        "FROM emotion_history" + where + " ORDER BY timestamp DESC"
    )
    database = _db()
    try:
        with database.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()
    finally:
        database.close()


def _record(row):
    timestamp = row.get("timestamp")
    return {
        "id": row.get("id"),
        "device_id": row.get("device_id"),
        "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S") if timestamp else None,
        "dominant": row.get("dominant"),
        "score": float(row.get("score") or 0),
        "belief": _safe_belief(row.get("belief_json")),
        "conflict": float(row.get("conflict") or 0),
        "high_conflict": bool(row.get("high_conflict")),
        "snr": float(row["snr"]) if row.get("snr") is not None else None,
        "lux": float(row["lux"]) if row.get("lux") is not None else None,
        "vision_reliability": float(row["vision_reliability"]) if row.get("vision_reliability") is not None else None,
        "audio_reliability": float(row["audio_reliability"]) if row.get("audio_reliability") is not None else None,
    }


async def handle_history(request):
    try:
        aggregate = request.query.get("aggregate", "day")
        if aggregate not in AGGREGATE_FORMATS:
            raise ValueError("aggregate must be hour, day, week, or month")
        rows = _load_rows(request.query)
        summary = _summary(rows)
        data = {
            "records": [_record(row) for row in rows],
            "trend": _trend(rows, aggregate),
            **summary,
        }
        return _cors(web.json_response({"code": 0, "data": data}))
    except ValueError as exc:
        return _cors(web.json_response({"code": 400, "msg": str(exc), "data": None}, status=400))
    except Exception:
        return _cors(web.json_response({"code": 500, "msg": "history query failed", "data": None}, status=500))


async def handle_stats(request):
    try:
        rows = _load_rows(request.query)
        return _cors(web.json_response({"code": 0, "data": _summary(rows)}))
    except ValueError as exc:
        return _cors(web.json_response({"code": 400, "msg": str(exc), "data": None}, status=400))
    except Exception:
        return _cors(web.json_response({"code": 500, "msg": "statistics query failed", "data": None}, status=500))
