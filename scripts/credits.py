"""Track Google Flow credits per Google account (you can have several AI Pro accounts).

A film is made when ANY account can afford it; when all are low, the day's video is stickman.
The real numbers live in Flow (profile menu); the daily clip task records them here:

    python scripts/credits.py set 640 --account you@gmail.com --resets 2026-12-21
    python scripts/credits.py show
    python scripts/credits.py check 11          # exit code 0 = some account can afford an 11-shot film
    python scripts/credits.py best 11           # prints the account to use (or nothing)

Unknown numbers count as "probably enough" (the clip task re-checks in Flow before spending).
"""
import argparse
import datetime as dt
import sys

from common import STATE, load_config, read_json, write_json

LEDGER = STATE / "credits.json"
DEFAULT = "default"


def _cfg() -> dict:
    return load_config().get("cinematic", {})


def _load() -> dict:
    led = read_json(LEDGER) if LEDGER.exists() else {}
    if "accounts" not in led:  # migrate the old single-account format
        old = {k: led[k] for k in ("remaining", "checked_at", "resets_on") if k in led}
        led = {"accounts": {DEFAULT: old} if old else {}}
    return led


def _next_reset(after: dt.date, day: int) -> dt.date:
    day = max(1, min(28, day))
    d = after.replace(day=day)
    if d <= after:
        d = (after.replace(day=1) + dt.timedelta(days=32)).replace(day=day)
    return d


def _estimate(acc: dict) -> int | None:
    if acc.get("remaining") is None:
        return None
    remaining = int(acc["remaining"])
    checked = dt.date.fromisoformat(str(acc.get("checked_at", dt.date.today().isoformat()))[:10])
    resets = acc.get("resets_on")
    reset_date = dt.date.fromisoformat(resets) if resets else _next_reset(checked, int(_cfg().get("credit_reset_day", 1)))
    if dt.date.today() >= reset_date:
        remaining = max(remaining, int(_cfg().get("monthly_credits", 1000)))
    return remaining


def accounts() -> dict[str, int | None]:
    return {name: _estimate(a) for name, a in _load()["accounts"].items()}


def estimate() -> int | None:
    """Best single-account balance (a film's clips are made on one account at a time)."""
    vals = list(accounts().values())
    if not vals or any(v is None for v in vals):
        return None
    return max(vals)


def film_cost(shots: int) -> int:
    c = _cfg()
    return int(round(shots * float(c.get("credits_per_clip", 10)) * (1 + float(c.get("redo_margin", 0.3))))) \
        + int(c.get("credit_reserve", 0))


def best_account(shots: int) -> str | None:
    cost = film_cost(shots)
    accs = accounts()
    for name, rem in accs.items():
        if rem is None or rem >= cost:
            return name
    return None if accs else DEFAULT


def can_afford(shots: int) -> bool | None:
    accs = accounts()
    if not accs:
        return None
    return best_account(shots) is not None


def record(remaining: int, account: str | None = None, resets_on: str | None = None) -> None:
    led = _load()
    name = account or DEFAULT
    if account and DEFAULT in led["accounts"] and len(led["accounts"]) == 1 and account != DEFAULT:
        led["accounts"].pop(DEFAULT)  # replace the anonymous entry once real account names arrive
    acc = led["accounts"].setdefault(name, {})
    acc.update(remaining=int(remaining), checked_at=dt.datetime.now().isoformat(timespec="seconds"))
    if resets_on:
        acc["resets_on"] = resets_on
    elif acc.get("resets_on") and dt.date.fromisoformat(acc["resets_on"]) <= dt.date.today():
        acc.pop("resets_on")
    write_json(LEDGER, led)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("set"); s.add_argument("remaining", type=int); s.add_argument("--account"); s.add_argument("--resets")
    sub.add_parser("show")
    c = sub.add_parser("check"); c.add_argument("shots", type=int)
    b = sub.add_parser("best"); b.add_argument("shots", type=int)
    a = ap.parse_args()
    if a.cmd == "set":
        record(a.remaining, a.account, a.resets)
    elif a.cmd == "best":
        print(best_account(a.shots) or "")
        return
    elif a.cmd == "check":
        ok = can_afford(a.shots)
        print(f"film of {a.shots} shots needs ~{film_cost(a.shots)} credits; accounts: {accounts() or 'none recorded'}")
        print("OK" if ok is not False else "NOT ENOUGH on any account -> stickman")
        sys.exit(0 if ok is not False else 1)
    led = _load()["accounts"]
    if not led:
        print("no credits recorded yet (the daily clip task records them from Flow)")
    for name, acc in led.items():
        print(f"{name}: ~{_estimate(acc)} credits | checked {acc.get('checked_at', 'never')} "
              f"| refresh {acc.get('resets_on', 'day ' + str(_cfg().get('credit_reset_day', 1)))}")


if __name__ == "__main__":
    main()
