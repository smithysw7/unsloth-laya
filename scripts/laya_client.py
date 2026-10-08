#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Laya decision-model client for Unsloth Studio's Decision API (POST /v1/systemone).

Zero dependencies: Python 3.8+ standard library only.

Config resolution order:
  1. --url / --api-key / --model CLI flags
  2. UNSLOTH_LAYA_URL / UNSLOTH_API_KEY / UNSLOTH_LAYA_MODEL env vars
  3. ~/.unsloth-laya/config.json   (see templates/config.example.json)

CLI examples:
  python laya_client.py --check
  python laya_client.py --state "ticket text" \
      --questions '{"refund": {"type": "noul", "instructions": "Does the customer ask for a refund?"}}'
  python laya_client.py --state "工单文本" --questions-file questions.json --pretty

As a module:
  from laya_client import ask
  result = ask(state="text", questions={...})

Exit codes: 0 = ok, 1 = usage error, 2 = API/HTTP error, 3 = config missing, 4 = bad question schema
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_URL = "http://127.0.0.1:8888"
ENDPOINT = "/v1/systemone"
CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".unsloth-laya", "config.json")
VALID_TYPES = ("noul", "choice", "score")


def _load_config(cli):
    """Merge CLI flags > env vars > config file. Returns (url, api_key, model)."""
    url, api_key, model = cli.get("url"), cli.get("api_key"), cli.get("model")
    if not url:
        url = os.environ.get("UNSLOTH_LAYA_URL")
    if not api_key:
        api_key = os.environ.get("UNSLOTH_API_KEY")
    if not model:
        model = os.environ.get("UNSLOTH_LAYA_MODEL")
    if not (url and api_key):
        if os.path.isfile(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                url = url or cfg.get("url")
                api_key = api_key or cfg.get("api_key")
                model = model or cfg.get("model")
            except (OSError, ValueError) as e:
                print(f"config file unreadable ({CONFIG_PATH}): {e}", file=sys.stderr)
                sys.exit(3)
    if not url:
        url = DEFAULT_URL
    if not api_key:
        print(
            "No API key found. Set UNSLOTH_API_KEY or create " + CONFIG_PATH
            + " (see templates/config.example.json). Key lives in "
            "Settings -> API -> Access tokens in Unsloth Studio.",
            file=sys.stderr,
        )
        sys.exit(3)
    return url.rstrip("/"), api_key, model or "laya"


def _validate_questions(questions):
    """Fail fast with a readable message instead of a 422 from the server."""
    if not isinstance(questions, dict) or not questions:
        print("--questions must be a non-empty JSON object of questions.", file=sys.stderr)
        sys.exit(4)
    if len(questions) > 64:
        print("Max 64 questions per request.", file=sys.stderr)
        sys.exit(4)
    for name, q in questions.items():
        if not isinstance(q, dict) or q.get("type") not in VALID_TYPES:
            print(
                f"question '{name}': 'type' must be one of {VALID_TYPES}.", file=sys.stderr
            )
            sys.exit(4)
        if not q.get("instructions"):
            print(f"question '{name}': 'instructions' is required.", file=sys.stderr)
            sys.exit(4)
        if q["type"] == "choice":
            crit = q.get("criteria")
            if not isinstance(crit, dict) or not crit:
                print(f"choice '{name}': 'criteria' must be {{label: description, ...}}.", file=sys.stderr)
                sys.exit(4)
            if len(crit) > 255:
                print(f"choice '{name}': max 255 options.", file=sys.stderr)
                sys.exit(4)
        if q["type"] == "score":
            crit = q.get("criteria")
            if not isinstance(crit, list) or not 2 <= len(crit) <= 10:
                print(f"score '{name}': 'criteria' must be a list of 2-10 level labels.", file=sys.stderr)
                sys.exit(4)


def _post(url, api_key, payload, timeout):
    req = urllib.request.Request(
        url + ENDPOINT,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:500]
        print(f"HTTP {e.code}: {body}", file=sys.stderr)
        if e.code in (401, 403):
            print("-> Key wrong or rotated. Regenerate in Settings -> API -> Access tokens.", file=sys.stderr)
        sys.exit(2)
    except urllib.error.URLError as e:
        print(f"Connection failed: {e.reason}", file=sys.stderr)
        print("-> Is Unsloth Studio running? Is the Decision API enabled (Settings -> API)?", file=sys.stderr)
        sys.exit(2)


def ask(state, questions, model="laya", url=None, api_key=None, timeout=60):
    """Send one decision request. Returns the parsed response dict."""
    cli = {"url": url, "api_key": api_key, "model": model}
    real_url, real_key, real_model = _load_config(cli)
    _validate_questions(questions)
    return _post(real_url, real_key, {"model": real_model, "state": state, "questions": questions}, timeout)


def _summarize(answers):
    lines = []
    for name, a in answers.items():
        t = a.get("type")
        if t == "noul":
            p = a.get("noul", 0.0)
            lines.append(f"{name}: {p:.4f} yes-probability")
        elif t == "choice":
            probs = a.get("probabilities", {})
            top = max(probs, key=probs.get) if probs else "?"
            lines.append(f"{name}: {a.get('choice', '?')} (p={probs.get(top, 0):.4f})")
        elif t == "score":
            legend = a.get("legend", {})
            hi = max((int(k) for k in legend), default=0)
            lines.append(f"{name}: {a.get('score', 0):.2f} / {hi}")
    return "\n".join(lines)


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Laya decision-model client for Unsloth Studio")
    ap.add_argument("--state", help="text (or JSON) to make decisions about")
    ap.add_argument("--questions", help="questions as inline JSON")
    ap.add_argument("--questions-file", help="questions as a JSON file")
    ap.add_argument("--model", help="laya (default) / default / jev-latest / laya-multilingual / laya-english")
    ap.add_argument("--url", help="Unsloth Studio base URL (default http://127.0.0.1:8888)")
    ap.add_argument("--api-key", help="access token (prefer env/config file; never commit it)")
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--check", action="store_true", help="probe connectivity (GET /v1/models) and exit")
    ap.add_argument("--pretty", action="store_true", help="print a human summary before the raw JSON")
    args = ap.parse_args(argv)

    url, api_key, model = _load_config({"url": args.url, "api_key": args.api_key, "model": args.model})

    if args.check:
        req = urllib.request.Request(
            url + "/v1/models", headers={"Authorization": "Bearer " + api_key}
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            print(f"OK: Unsloth Studio reachable at {url}; {len(data.get('data', []))} models listed.")
            print(f"Decision endpoint: {url + ENDPOINT}")
            return
        except Exception as e:
            print(f"Check failed: {e}", file=sys.stderr)
            sys.exit(2)

    if not args.state or not (args.questions or args.questions_file):
        ap.error("--state and (--questions | --questions-file) are required (or use --check)")

    if args.questions_file:
        with open(args.questions_file, "r", encoding="utf-8") as f:
            questions = json.load(f)
    else:
        questions = json.loads(args.questions)

    result = ask(args.state, questions, model=model, url=url, api_key=api_key, timeout=args.timeout)
    answers = result.get("answers", {})
    if args.pretty:
        print(_summarize(answers))
        print("-" * 40)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
