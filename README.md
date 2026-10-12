# Reed-Solomon Error-Correcting Codes

A standalone, zero-dependency implementation of [Reed-Solomon error-correcting
codes](https://en.wikipedia.org/wiki/Reed%E2%80%93Solomon_error_correction) over
the Galois field GF(2^8), built from first principles for learning purposes.

Author: [Nathan Kimutai (tekindet)](https://github.com/tekindet)

## Overview

Reed-Solomon codes add redundant (parity) symbols to a message so that errors
introduced during transmission or storage can be detected and corrected. This
project implements the underlying machinery from scratch:

- **Finite field arithmetic** — multiplication, division, addition, and
  exponentiation over GF(2^8) using log/antilog tables.
- **Polynomial arithmetic** — addition, multiplication, and polynomial
  division over GF(2^8) via a `GF256Poly` class.
- **Generator polynomial** — builds `G(x) = (x - α^0)(x - α^1) ... (x - α^(n-1))`
  for a chosen number of parity symbols `nsym`.
- **Encoding** — computes parity symbols as the remainder of the message
  polynomial divided by the generator, producing the final codeword.

## Project status

Working end to end: encoding, syndrome computation, Berlekamp&ndash;Massey error
location, Chien search, and Forney error magnitudes all round-trip correctly.

## Interactive demo

A small Flask web app walks through the whole pipeline: encode a message,
corrupt up to `t = nsym / 2` bytes by clicking them, then decode and watch each
stage (syndromes, error locator, Chien search, Forney, corrected codeword)
produced live.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open <http://127.0.0.1:5000>.

## Deploying for free (Render)

The repo includes a [`render.yaml`](render.yaml) blueprint, so Render can build
and run it with no manual configuration.

1. Push this project to a GitHub repository.
2. Create a free account at <https://render.com> and choose **New → Blueprint**.
3. Select the repository. Render reads `render.yaml` and provisions a free web
   service (`gunicorn app:app`, health check on `/`).
4. Wait for the first deploy, then open the `*.onrender.com` URL.

Notes on the free tier: the instance sleeps after ~15 minutes of inactivity and
takes a few seconds to wake on the next request. No credit card is required.

To configure a service manually instead of using the blueprint, set:

- **Build command:** `pip install -r requirements.txt`
- **Start command:** `gunicorn app:app --bind 0.0.0.0:$PORT`
- **Health check path:** `/`

## Usage

```python
from main import build_generator_poly, GF256Poly

msg = "this is a test message"
nsym = 4  # number of parity (redundancy) symbols

msg_bytes = [ord(c) for c in msg]

M_x = GF256Poly(msg_bytes)          # message polynomial
G_x = build_generator_poly(nsym)    # generator polynomial

# Shift the message by nsym degrees, then divide by G(x);
# the remainder P(x) is the parity. Codeword = message + parity.
shift_factor = GF256Poly([1] + [0] * nsym)
M_shifted = M_x * shift_factor
Q_x, P_x = M_shifted.divmod(G_x)
C_x = M_shifted + P_x

print(f"Final Codeword C(x):\n{C_x}")
```

Running the module directly executes the example above:

```bash
python main.py
```

## Running tests

Tests use the standard library `unittest` module — no dependencies needed.

```bash
python3 -m unittest test_main -v
```

Or run a single test:

```bash
python3 -m unittest test_main.TestBerlekampMassey.test_single_error_locator_root -v
```

## How it works

1. Represent the message bytes as the coefficients of a polynomial `M(x)` over
   GF(2^8).
2. Build the generator polynomial `G(x)` from consecutive powers of `α` (the
   primitive element of the field).
3. Shift `M(x)` by `nsym` degrees and divide by `G(x)`.
4. Append the remainder `P(x)` — the parity symbols — to the message. The
   resulting codeword `C(x)` is divisible by `G(x)`, which is what later allows
   errors to be detected and corrected.

## Roadmap

- [x] GF(2^8) arithmetic (add, multiply, divide, pow)
- [x] Polynomial arithmetic over GF(2^8)
- [x] Generator polynomial construction
- [x] Encoding (codeword generation)
- [x] Syndrome calculation
- [x] Decoding / error location (Berlekamp–Massey, Chien search)
- [x] Error correction and full end-to-end round-trip
- [x] Interactive Flask demo UI

## License

Not yet licensed.
