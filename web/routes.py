import json


def get_response(path):
    if path == "/health":
        body = {
            "status": "ok",
            "application": "uncle-toolkit",
            "mode": "local",
        }
        return 200, body

    return 404, {"detail": "Not found"}


def encode_json(data):
    return json.dumps(
        data,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
