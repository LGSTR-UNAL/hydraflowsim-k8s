"""Generate promtool fixtures for the actual ScaledObject query (requires PyYAML).

Usage: python3 tests/generate_autoscaling_promql_test.py > /tmp/autoscaling-test.yaml
       promtool test rules /tmp/autoscaling-test.yaml
"""

from pathlib import Path
import sys

import yaml


path = Path(__file__).resolve().parents[1] / "services/sim-workers-scaledobject.yaml"
query = yaml.safe_load(path.read_text())["spec"]["triggers"][0]["metadata"]["query"]
group = 'namespace="hydraflowsim",consumergroup="sim-workers"'
partition = group + ',topic="hydraflowsim.streaming.simulations",partition="0"'


def series(name, labels, value):
    return {"series": name + "{" + labels + "}", "values": " ".join([str(value)] * 3)}


def case(name, lag=900, success=1, available=1, last_success=120, extra=None,
         expected=900, missing=False):
    inputs = [] if missing else [
        series("kafka_sharegroup_lag", partition + ',pod="exporter-a"', lag),
        series("kafka_sharegroup_exporter_scrape_success", group, success),
        series("kafka_sharegroup_exporter_last_success_timestamp_seconds", group, last_success),
        series("kafka_sharegroup_lag_available", partition, available),
    ]
    inputs.extend(extra or [])
    return {
        "name": name,
        "interval": "1m",
        "input_series": inputs,
        "promql_expr_test": [{
            "expr": query,
            "eval_time": "2m",
            "exp_samples": [] if expected is None else [{"labels": "{}", "value": expected}],
        }],
    }


tests = [
    case("healthy backlog"),
    case("healthy zero is a valid metric", lag=0, expected=0),
    case("failed collection is not zero", success=0, expected=None),
    case("Kafka lag unavailable is not zero", available=0, expected=None),
    case("stale collection is not zero", last_success=0, expected=None),
    case("missing exporter is not zero", missing=True, expected=None),
    case("rolling exporter overlap is deduplicated", extra=[
        series("kafka_sharegroup_lag", partition + ',pod="exporter-b"', 900),
    ]),
    case("lag is summed across partitions", extra=[
        series("kafka_sharegroup_lag", partition.replace('partition="0"', 'partition="1"'), 300),
    ], expected=1200),
    case("other groups and topics do not affect HydraFlowSim", extra=[
        series("kafka_sharegroup_lag", partition.replace("sim-workers", "other-group"), 99999),
        series("kafka_sharegroup_lag", partition.replace("hydraflowsim.streaming.simulations", "other-topic"), 99999),
    ]),
]
yaml.safe_dump({"rule_files": [], "evaluation_interval": "1m", "tests": tests}, sys.stdout)
