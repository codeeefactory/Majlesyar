#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


def load_json(path: Path | None) -> dict:
    if path is None or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def probe_fresh(probe: dict, max_age_seconds: int) -> bool:
    timestamp = parse_timestamp(probe.get("timestamp"))
    if timestamp is None:
        return False
    return datetime.now(timezone.utc) - timestamp <= timedelta(seconds=max_age_seconds)


def probe_origin_ok(probe: dict, origin_name: str) -> bool:
    return bool(((probe.get("origins") or {}).get(origin_name) or {}).get("overall_ok"))


def apply_hysteresis(
    name: str,
    observed_up: bool,
    history: dict,
    failure_threshold: int,
    success_threshold: int,
) -> tuple[bool, dict]:
    previous = history.get(name) or {
        "effective_up": observed_up,
        "successes": 0,
        "failures": 0,
    }
    if observed_up:
        previous["successes"] = int(previous.get("successes", 0)) + 1
        previous["failures"] = 0
        if previous.get("effective_up", True):
            previous["effective_up"] = True
        elif previous["successes"] >= success_threshold:
            previous["effective_up"] = True
    else:
        previous["failures"] = int(previous.get("failures", 0)) + 1
        previous["successes"] = 0
        if not previous.get("effective_up", True):
            previous["effective_up"] = False
        elif previous["failures"] >= failure_threshold:
            previous["effective_up"] = False

    history[name] = previous
    return bool(previous["effective_up"]), history


def decide_policy(
    iran_origin_up: bool,
    global_origin_up: bool,
    global_reachable_from_iran: bool,
    iran_reachable_from_global: bool,
) -> tuple[dict, str]:
    if iran_origin_up and global_origin_up:
        return {"iran": "iran", "default": "global"}, "Both origin pools healthy."
    if not iran_origin_up and global_origin_up:
        return {
            "iran": "global" if global_reachable_from_iran else "maintenance",
            "default": "global",
        }, "Iran origin unhealthy."
    if iran_origin_up and not global_origin_up:
        return {
            "iran": "iran",
            "default": "iran" if iran_reachable_from_global else "maintenance",
        }, "Global origin unhealthy."
    return {"iran": "maintenance", "default": "maintenance"}, "Both origin pools unhealthy."


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate probe results into an effective GeoDNS failover state.")
    parser.add_argument("--iran-probe", required=True, type=Path)
    parser.add_argument("--global-probe", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--history", required=True, type=Path)
    parser.add_argument("--manual-override", type=Path)
    parser.add_argument("--failure-threshold", type=int, default=3)
    parser.add_argument("--success-threshold", type=int, default=2)
    parser.add_argument("--max-probe-age-seconds", type=int, default=180)
    args = parser.parse_args()

    history = load_json(args.history)
    manual_override = load_json(args.manual_override)
    if manual_override.get("enabled"):
        state = {
            "mode": "manual",
            "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "reason": manual_override.get("reason", "Manual override active."),
            "policy": manual_override["policy"],
            "effective_health": {},
            "serial": int(datetime.now(timezone.utc).strftime("%Y%m%d%H")),
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(state, indent=2), encoding="utf-8")
        return

    iran_probe = load_json(args.iran_probe)
    global_probe = load_json(args.global_probe)

    iran_fresh = probe_fresh(iran_probe, args.max_probe_age_seconds)
    global_fresh = probe_fresh(global_probe, args.max_probe_age_seconds)

    observed_iran_origin_up = iran_fresh and probe_origin_ok(iran_probe, "iran")
    observed_global_origin_up = global_fresh and probe_origin_ok(global_probe, "global")
    observed_global_reachable_from_iran = iran_fresh and probe_origin_ok(iran_probe, "global")
    observed_iran_reachable_from_global = global_fresh and probe_origin_ok(global_probe, "iran")

    effective_iran_origin_up, history = apply_hysteresis(
        "iran_origin_up",
        observed_iran_origin_up,
        history,
        args.failure_threshold,
        args.success_threshold,
    )
    effective_global_origin_up, history = apply_hysteresis(
        "global_origin_up",
        observed_global_origin_up,
        history,
        args.failure_threshold,
        args.success_threshold,
    )
    effective_global_reachable_from_iran, history = apply_hysteresis(
        "global_reachable_from_iran",
        observed_global_reachable_from_iran,
        history,
        args.failure_threshold,
        args.success_threshold,
    )
    effective_iran_reachable_from_global, history = apply_hysteresis(
        "iran_reachable_from_global",
        observed_iran_reachable_from_global,
        history,
        args.failure_threshold,
        args.success_threshold,
    )

    policy, reason = decide_policy(
        effective_iran_origin_up,
        effective_global_origin_up,
        effective_global_reachable_from_iran,
        effective_iran_reachable_from_global,
    )
    state = {
        "mode": "automatic",
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "reason": reason,
        "policy": policy,
        "effective_health": {
            "iran_origin_up": effective_iran_origin_up,
            "global_origin_up": effective_global_origin_up,
            "global_reachable_from_iran": effective_global_reachable_from_iran,
            "iran_reachable_from_global": effective_iran_reachable_from_global,
        },
        "observed_health": {
            "iran_probe_fresh": iran_fresh,
            "global_probe_fresh": global_fresh,
            "iran_origin_up": observed_iran_origin_up,
            "global_origin_up": observed_global_origin_up,
            "global_reachable_from_iran": observed_global_reachable_from_iran,
            "iran_reachable_from_global": observed_iran_reachable_from_global,
        },
        "serial": int(datetime.now(timezone.utc).strftime("%Y%m%d%H")),
    }

    args.history.parent.mkdir(parents=True, exist_ok=True)
    args.history.write_text(json.dumps(history, indent=2), encoding="utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(state, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
