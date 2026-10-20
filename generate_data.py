import argparse
import json
import random
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

"""for d in 01 02 03 04 05 06 07; do python generator/generate_events.py --date 2026-10-$d; doneGenerate one day of fake game events as JSON lines, with deliberate dirty data.

Usage:
    python generator/generate_events.py --date 2026-10-01
"""

N_PLAYERS = 500
EVENTS_PER_DAY = 5000
COUNTRIES = ["CA", "US", "AU", "GB", "NZ"]
DEVICES = ["ios", "android", "web"]
EVENT_WEIGHTS = {"session_start": 25, "game_round": 50, "purchase": 5, "session_end": 20}
PRICES = [0.99, 4.99, 9.99, 19.99]
START = date(2026, 10, 1)  # first day of simulated history


def build_players() -> list[dict]:
    """Same player pool every run (fixed seed). ~5% of players switch device on some day."""
    rng = random.Random(42)
    players = []
    for i in range(1, N_PLAYERS + 1):
        device = rng.choice(DEVICES)
        switch = rng.random() < 0.05
        players.append({
            "player_id": f"p_{i:04d}",
            "email": f"player{i}@example.com",
            "country": rng.choice(COUNTRIES),
            "device": device,
            "new_device": rng.choice([d for d in DEVICES if d != device]) if switch else None,
            "switch_on": START + timedelta(days=rng.randint(1, 10)) if switch else None,
        })
    return players


def device_on(player: dict, day: date) -> str:
    if player["new_device"] and day >= player["switch_on"]:
        return player["new_device"]
    return player["device"]


def make_event(rng: random.Random, player: dict, day: date) -> dict:
    event_type = rng.choices(list(EVENT_WEIGHTS), weights=EVENT_WEIGHTS.values())[0]
    ts = datetime(day.year, day.month, day.day, tzinfo=timezone.utc) + timedelta(seconds=rng.randint(0, 86399))
    event = {
        "event_id": str(uuid.UUID(int=rng.getrandbits(128))),
        "event_type": event_type,
        "event_ts": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "player_id": player["player_id"],
        "email": player["email"],
        "device": device_on(player, day),
        "country": player["country"],
        "amount_usd": rng.choice(PRICES) if event_type == "purchase" else None,
        "schema_version": 1,
    }
    if rng.random() < 0.2:  # schema v2 adds a field
        event["schema_version"] = 2
        event["app_version"] = rng.choice(["3.1.0", "3.2.0"])
    return event


def generate(day: date) -> list[dict]:
    rng = random.Random(day.isoformat())  # same date -> same file
    players = build_players()
    events = [make_event(rng, rng.choice(players), day) for _ in range(EVENTS_PER_DAY)]

    # --- deliberate dirty data ---
    for e in rng.sample(events, k=EVENTS_PER_DAY // 100):  # ~1% late: belongs to yesterday
        ts = datetime.strptime(e["event_ts"], "%Y-%m-%dT%H:%M:%SZ") - timedelta(days=1)
        e["event_ts"] = ts.strftime("%Y-%m-%dT%H:%M:%SZ")
    purchases = [e for e in events if e["event_type"] == "purchase"]
    for e in rng.sample(purchases, k=min(5, len(purchases))):  # bad amounts
        e["amount_usd"] = rng.choice([-4.99, None])
    events += [dict(e) for e in rng.sample(events, k=EVENTS_PER_DAY // 100)]  # ~1% duplicates

    rng.shuffle(events)
    return events


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--out", default="data/raw")
    args = parser.parse_args()

    day = date.fromisoformat(args.date)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"events_{day.isoformat()}.jsonl"
    events = generate(day)
    with path.open("w") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")
    print(f"wrote {len(events)} events to {path}")


if __name__ == "__main__":
    main()