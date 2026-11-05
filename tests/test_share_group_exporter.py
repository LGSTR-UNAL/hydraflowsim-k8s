import importlib.util
from pathlib import Path
import subprocess
import time
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "exporter", Path(__file__).resolve().parents[1] /
    "observability/share-group-exporter/exporter.py",
)
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)

GROUP = "sim-workers"
HEADER = "GROUP TOPIC PARTITION START-OFFSET LAG\n"
OUTPUT = HEADER + GROUP + " hydraflowsim.streaming.simulations 0 12374 7\n"


class ShareGroupExporterTest(unittest.TestCase):
    def test_parses_kafka_lag_and_unavailable_value(self):
        self.assertEqual(exporter.parse_offsets(
            OUTPUT + GROUP + " hydraflowsim.streaming.simulations 1 42 -\n", GROUP,
        ), [("hydraflowsim.streaming.simulations", 0, 12374, 7),
            ("hydraflowsim.streaming.simulations", 1, 42, None)])

    def test_rejects_missing_group_malformed_output_and_negative_lag(self):
        for output in ["Error: Group not found", HEADER, GROUP + " topic 0 1 2",
                       HEADER + GROUP + " topic 0 1 -1\n",
                       HEADER + GROUP + " topic 0 bad 2\n"]:
            with self.subTest(output=output), self.assertRaises(ValueError):
                exporter.parse_offsets(output, GROUP)

    def test_uses_actual_lag_instead_of_start_offset(self):
        collector = exporter.Collector(GROUP, "kafka:9092")
        with patch.object(exporter.subprocess, "run", return_value=
                          subprocess.CompletedProcess([], 0, OUTPUT, "")) as run:
            collector.collect()
        self.assertIn("--offsets", run.call_args.args[0])
        metrics = collector.metrics()
        self.assertIn('partition="0"} 7\n', metrics)
        self.assertIn('partition="0"} 12374\n', metrics)
        self.assertIn('scrape_success{consumergroup="' + GROUP + '"} 1\n', metrics)

    def test_unavailable_lag_is_not_zero(self):
        collector = exporter.Collector(GROUP, "kafka:9092")
        collector.success = True
        collector.last_success = time.time()
        collector.rows = [("topic", 0, 42, None)]
        metrics = collector.metrics()
        self.assertIn('kafka_sharegroup_lag_available{consumergroup="' + GROUP +
                      '",topic="topic",partition="0"} 0\n', metrics)
        self.assertFalse(any(line.startswith("kafka_sharegroup_lag{")
                             for line in metrics.splitlines()))

    def test_query_timeout_clears_previous_lag(self):
        collector = exporter.Collector(GROUP, "kafka:9092")
        collector.rows = [("topic", 0, 42, 7)]
        collector.success = True
        collector.last_success = time.time()
        with patch.object(exporter.subprocess, "run", side_effect=
                          subprocess.TimeoutExpired("kafka-share-groups.sh", 20)):
            with self.assertLogs(level="ERROR"):
                collector.collect()
        self.assertEqual(collector.errors, 1)
        self.assertEqual(collector.rows, [])
        self.assertIn('scrape_success{consumergroup="' + GROUP + '"} 0\n', collector.metrics())

    def test_stale_results_are_not_reported_as_current_lag(self):
        collector = exporter.Collector(GROUP, "kafka:9092")
        collector.success = True
        collector.last_success = time.time() - 60
        collector.rows = [("topic", 0, 42, 7)]
        self.assertFalse(any(line.startswith("kafka_sharegroup_lag{")
                             for line in collector.metrics().splitlines()))

    def test_prometheus_labels_are_escaped(self):
        self.assertEqual(exporter.label('a"b\\c\nd'), 'a\\"b\\\\c\\nd')


if __name__ == "__main__":
    unittest.main()
