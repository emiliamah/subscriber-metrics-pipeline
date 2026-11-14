"""Generate fake subscription events, one CSV file per day.

Each user moves through simple states:
    (new) --signup--> active on a plan --cancel--> cancelled --reactivate--> active
    While active, a user can upgrade or downgrade between plans.

About 1% of rows are deliberately broken, so the data quality checks
have something real to catch later.

Run from the project folder:
    python src/generate_events.py --start 2026-10-01 --days 30
"""
import argparse
import csv
import random
from datetime import date, datetime, timedelta
from pathlib import Path

# Same seed = same "random" data every run. This makes bugs reproducible.
random.seed(42)

# Plans from cheapest to most expensive, with monthly price in USD.
PLANS = {"basic_ads": 7.99, "premium": 15.99, "bundle": 24.99}
PLAN_ORDER = list(PLANS)  # ["basic_ads", "premium", "bundle"]
SIGNUP_WEIGHTS = [0.5, 0.35, 0.15]  # most new users pick the cheap plan

COUNTRIES = ["US", "CA", "GB", "MX", "BR"]

# Daily chances for each user.
P_CANCEL = 0.010
P_UPGRADE = 0.005
P_DOWNGRADE = 0.003
P_REACTIVATE = 0.010  # for users who already cancelled

NEW_SIGNUPS_PER_DAY = (80, 120)  # a random number in this range each day
BAD_ROW_RATE = 0.01

OUTPUT_DIR = Path("data/raw")
FIELDS = ["event_id", "user_id", "event_type", "plan_id", "event_ts", "price_usd", "country"]

event_counter = 0


def make_event(user_id, event_type, plan_id, day, country):
    """Build one event row at a random time during `day`."""
    global event_counter
    event_counter += 1
    seconds = random.randint(0, 86_399)
    ts = datetime.combine(day, datetime.min.time()) + timedelta(seconds=seconds)
    price = 0.0 if event_type == "cancel" else PLANS[plan_id]
    return {
        "event_id": f"evt_{event_counter:07d}",
        "user_id": user_id,
        "event_type": event_type,
        "plan_id": plan_id,
        "event_ts": ts.isoformat(),
        "price_usd": price,
        "country": country,
    }


def simulate_existing_users(users, day):
    """Decide what each existing user does today."""
    events = []
    for user_id, user in users.items():
        plan = user["plan"]

        if plan is None:  # cancelled user
            if random.random() < P_REACTIVATE:
                user["plan"] = random.choice(PLAN_ORDER)
                events.append(make_event(user_id, "reactivate", user["plan"], day, user["country"]))
            continue

        roll = random.random()
        level = PLAN_ORDER.index(plan)

        if roll < P_CANCEL:
            events.append(make_event(user_id, "cancel", plan, day, user["country"]))
            user["plan"] = None
        elif roll < P_CANCEL + P_UPGRADE and level < len(PLAN_ORDER) - 1:
            user["plan"] = PLAN_ORDER[level + 1]
            events.append(make_event(user_id, "upgrade", user["plan"], day, user["country"]))
        elif roll < P_CANCEL + P_UPGRADE + P_DOWNGRADE and level > 0:
            user["plan"] = PLAN_ORDER[level - 1]
            events.append(make_event(user_id, "downgrade", user["plan"], day, user["country"]))
    return events


def add_new_signups(users, day, next_user_number):
    """Create today's brand-new subscribers."""
    events = []
    for _ in range(random.randint(*NEW_SIGNUPS_PER_DAY)):
        user_id = f"user_{next_user_number:05d}"
        next_user_number += 1
        plan = random.choices(PLAN_ORDER, weights=SIGNUP_WEIGHTS)[0]
        country = random.choice(COUNTRIES)
        users[user_id] = {"plan": plan, "country": country}
        events.append(make_event(user_id, "signup", plan, day, country))
    return events, next_user_number


def inject_bad_rows(events, day):
    """Break about 1% of rows on purpose, in four different ways."""
    result = []
    for event in events:
        result.append(event)
        if random.random() >= BAD_ROW_RATE:
            continue
        problem = random.choice(["duplicate", "null_user", "bad_plan", "orphan_cancel"])
        if problem == "duplicate":
            result.append(dict(event))  # exact copy, same event_id
        elif problem == "null_user":
            event["user_id"] = ""  # missing user
        elif problem == "bad_plan":
            event["plan_id"] = "platinum"  # plan that doesn't exist
        elif problem == "orphan_cancel":
            # a cancel for a user who never signed up
            result.append(make_event("user_99999", "cancel", "premium", day, "US"))
    return result


def write_csv(events, day):
    path = OUTPUT_DIR / f"events_{day.isoformat()}.csv"
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(events)
    return path


def main():
    parser = argparse.ArgumentParser(description="Generate fake subscription events.")
    parser.add_argument("--start", default="2026-10-01", help="first day, YYYY-MM-DD")
    parser.add_argument("--days", type=int, default=30, help="how many days to generate")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    start = date.fromisoformat(args.start)

    users = {}  # user_id -> {"plan": plan or None, "country": ...}
    next_user_number = 1

    for i in range(args.days):
        day = start + timedelta(days=i)
        events = simulate_existing_users(users, day)
        new_events, next_user_number = add_new_signups(users, day, next_user_number)
        events += new_events
        events.sort(key=lambda e: e["event_ts"])
        events = inject_bad_rows(events, day)
        path = write_csv(events, day)
        active = sum(1 for u in users.values() if u["plan"] is not None)
        print(f"{day}  {len(events):>4} events  {active:>5} active subs  -> {path}")


if __name__ == "__main__":
    main()
