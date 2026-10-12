"""
Interactive demo server for the Reed-Solomon codec.

Serves a small educational UI that walks through encoding, channel
corruption, and error correction over GF(2^8). Run with:

    python app.py

then open http://127.0.0.1:5000
"""

from flask import Flask, jsonify, render_template, request

from main import GF256, RSCodec, build_generator_poly

app = Flask(__name__)

MAX_SYMBOLS = 255
MIN_NSYM = 2
MAX_NSYM = 30


def _codec(nsym):
    return RSCodec(MAX_SYMBOLS, MAX_SYMBOLS - nsym)


def _validate_message(message, nsym):
    if not isinstance(message, str):
        return "Message must be text."
    if message == "":
        return "Enter a non-empty message."
    if any(ord(c) > 255 for c in message):
        return "Only Latin-1 characters (code points 0-255) are supported."
    if ord(message[0]) == 0:
        return "Message cannot start with a NUL character."
    if nsym < MIN_NSYM or nsym > MAX_NSYM or nsym % 2 != 0:
        return f"Redundancy must be an even number between {MIN_NSYM} and {MAX_NSYM}."
    if len(message) + nsym > MAX_SYMBOLS:
        return f"Message + redundancy must fit in {MAX_SYMBOLS} symbols."
    return None


@app.route("/")
def index():
    return render_template("index.html")


@app.post("/api/encode")
def api_encode():
    data = request.get_json(silent=True) or {}
    message = data.get("message", "")
    nsym = data.get("nsym", 4)

    try:
        nsym = int(nsym)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid redundancy value."}), 400

    error = _validate_message(message, nsym)
    if error:
        return jsonify({"error": error}), 400

    codec = _codec(nsym)
    codeword = list(codec.encode(message).coeffs)
    message_bytes = [ord(c) for c in message]

    return jsonify(
        {
            "message": message,
            "message_bytes": message_bytes,
            "parity": codeword[len(message_bytes):],
            "codeword": codeword,
            "nsym": nsym,
            "t": nsym // 2,
            "generator": repr(build_generator_poly(nsym)),
        }
    )


@app.post("/api/decode")
def api_decode():
    data = request.get_json(silent=True) or {}
    codeword = data.get("codeword")
    nsym = data.get("nsym", 4)

    try:
        nsym = int(nsym)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid redundancy value."}), 400

    if nsym < MIN_NSYM or nsym > MAX_NSYM or nsym % 2 != 0:
        return jsonify({"error": "Invalid redundancy value."}), 400

    if not isinstance(codeword, list) or not codeword:
        return jsonify({"error": "Missing codeword."}), 400

    if any(not isinstance(b, int) or b < 0 or b > 255 for b in codeword):
        return jsonify({"error": "Codeword symbols must be bytes (0-255)."}), 400

    if len(codeword) > MAX_SYMBOLS:
        return jsonify({"error": f"Codeword cannot exceed {MAX_SYMBOLS} symbols."}), 400

    codec = _codec(nsym)
    length = len(codeword)

    syndromes = codec.decode(codeword)
    clean = all(s == 0 for s in syndromes)

    steps = {
        "syndromes": [
            {"index": i, "alpha": f"alpha^{i}", "value": s}
            for i, s in enumerate(syndromes)
        ],
        "clean": clean,
    }

    corrected = list(codeword)
    verified = clean

    if not clean:
        lambda_x = codec.berlekamp_massey(syndromes)
        positions = codec.chien_search(lambda_x, length)
        magnitudes = codec.forney_algorithm(syndromes, lambda_x, positions, length)

        for pos, mag in magnitudes.items():
            corrected[pos] = GF256.add(corrected[pos], mag)

        # Report every position Chien search tested, marking the roots.
        chien = []
        for i in range(length):
            x_inv = GF256.pow(2, (255 - (length - 1 - i)) % 255)
            chien.append(
                {
                    "index": i,
                    "exponent": (length - 1 - i) % 255,
                    "x_inv": x_inv,
                    "is_root": lambda_x.eval(x_inv) == 0,
                }
            )

        steps["error_locator"] = {
            "coeffs": lambda_x.coeffs,
            "pretty": repr(lambda_x),
        }
        steps["chien"] = chien
        steps["positions"] = positions
        steps["magnitudes"] = [
            {"index": pos, "value": magnitudes[pos]} for pos in positions
        ]

        verified = all(s == 0 for s in codec.decode(corrected))

    return jsonify(
        {
            "steps": steps,
            "corrected": corrected,
            "verified": verified,
        }
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
