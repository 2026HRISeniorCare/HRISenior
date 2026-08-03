"""Validated emotion persistence handler for Resona."""

import json
import os
import uuid

import pymysql
from aiohttp import web


EMOTIONS = {"happy", "sad", "neutral", "anger"}


def _response(payload, status=200):
    response = web.json_response(payload, status=status)
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


def _number(body, key, required=False):
    value = body.get(key)
    if value is None:
        if required:
            raise ValueError(f"{key} is required")
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be numeric") from exc


def _validate(body):
    if not isinstance(body, dict):
        raise ValueError("JSON object required")
    device_id = str(body.get("device_id") or "").strip()
    dominant = str(body.get("dominant") or "").strip().lower()
    belief = body.get("belief")
    if not device_id or len(device_id) > 64:
        raise ValueError("device_id is required and must not exceed 64 characters")
    if dominant not in EMOTIONS:
        raise ValueError("dominant must be happy, sad, neutral, or anger")
    if not isinstance(belief, list) or len(belief) != 4:
        raise ValueError("belief must contain four numeric values")
    try:
        belief = [float(value) for value in belief]
    except (TypeError, ValueError) as exc:
        raise ValueError("belief must contain four numeric values") from exc
    if any(value < 0 or value > 1 for value in belief):
        raise ValueError("belief values must be between 0 and 1")
    if not 0.99 <= sum(belief) <= 1.01:
        raise ValueError("belief values must sum to 1")
    score = _number(body, "score", required=True)
    conflict = _number(body, "conflict", required=True)
    if not 0 <= score <= 1 or not 0 <= conflict <= 1:
        raise ValueError("score and conflict must be between 0 and 1")
    return {
        "device_id": device_id,
        "dominant": dominant,
        "score": score,
        "belief": belief,
        "conflict": conflict,
        "high_conflict": bool(body.get("high_conflict")),
        "snr": _number(body, "snr"),
        "lux": _number(body, "lux"),
        "vision_reliability": _number(body, "vision_reliability"),
        "audio_reliability": _number(body, "audio_reliability"),
    }


async def handle_write(request):
    try:
        body = _validate(await request.json())
    except (ValueError, json.JSONDecodeError) as exc:
        return _response({"code": 400, "msg": str(exc), "data": None}, status=400)

    database = None
    try:
        database = pymysql.connect(
            host="127.0.0.1",
            user=os.environ.get("RESONA_DB_USER", "resona"),
            password=os.environ["RESONA_DB_PASSWORD"],
            database=os.environ.get("RESONA_DB_NAME", "xiaozhi_esp32_server"),
            connect_timeout=3,
        )
        with database.cursor() as cursor:
            cursor.execute(
                "INSERT INTO emotion_history "
                "(id, device_id, timestamp, dominant, score, belief_json, conflict, high_conflict, "
                "snr, lux, vision_reliability, audio_reliability) "
                "VALUES (%s, %s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    uuid.uuid4().hex[:32], body["device_id"], body["dominant"], body["score"],
                    json.dumps(body["belief"]), body["conflict"], 1 if body["high_conflict"] else 0,
                    body["snr"], body["lux"], body["vision_reliability"], body["audio_reliability"],
                ),
            )
        database.commit()
        return _response({"code": 0, "msg": "success", "data": None})
    except Exception:
        if database:
            database.rollback()
        return _response({"code": 500, "msg": "emotion write failed", "data": None}, status=500)
    finally:
        if database:
            database.close()
