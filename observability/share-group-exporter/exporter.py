"""Expose Kafka 4.2 Share Group lag reported by kafka-share-groups.sh."""

import logging
import os
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def parse_offsets(output, group):
    """Parse Kafka partition offsets; preserve unavailable offsets and lag as None."""
    rows = []
    header_seen = False
    for line in output.splitlines():
        fields = line.split()
        if fields == ["GROUP", "TOPIC", "PARTITION", "START-OFFSET", "LAG"]:
            header_seen = True
        elif fields and fields[0] == group:
            if not header_seen or len(fields) != 5:
                raise ValueError("Unexpected Share Group offset output")
            _, topic, partition, offset, lag = fields
            partition = int(partition)
            offset = None if offset == "-" else int(offset)
            lag = None if lag == "-" else int(lag)
            if lag is not None and lag < 0:
                raise ValueError("Share Group lag must be nonnegative")
            rows.append((topic, partition, offset, lag))
    if not header_seen or not rows:
        raise ValueError("No Share Group partition offsets returned")
    return rows


def label(value):
    """Escape a label value using Prometheus text exposition rules."""
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


class Collector:
    """Poll Kafka and expose a thread-safe snapshot of lag and query health."""

    def __init__(self, group, bootstrap, interval=30, timeout=20):
        self.group = group
        self.bootstrap = bootstrap
        self.interval = interval
        self.timeout = timeout
        self.lock = threading.Lock()
        self.rows = []
        self.success = False
        self.last_success = 0
        self.errors = 0

    def collect(self):
        """Replace cached offsets after a successful query; clear them on failure."""
        try:
            result = subprocess.run(
                [
                    "/opt/kafka/bin/kafka-share-groups.sh",
                    "--bootstrap-server",
                    self.bootstrap,
                    "--describe",
                    "--group",
                    self.group,
                    "--offsets",
                ],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=True,
            )
            rows = parse_offsets(result.stdout, self.group)
            with self.lock:
                self.rows = rows
                self.success = True
                self.last_success = time.time()
        except (subprocess.SubprocessError, OSError, ValueError) as error:
            logging.error("Share Group lag collection failed: %s", error)
            with self.lock:
                self.rows = []
                self.success = False
                self.errors += 1

    def run(self):
        """Poll repeatedly, accounting for query time in the polling interval."""
        while True:
            started = time.monotonic()
            self.collect()
            time.sleep(max(0, self.interval - (time.monotonic() - started)))

    def metrics(self):
        """Render metrics, omitting lag when the last observation is stale or failed."""
        with self.lock:
            rows = list(self.rows)
            last_success = self.last_success
            success = (
                self.success
                and time.time() - last_success <= self.interval + self.timeout
            )
            errors = self.errors
        group_labels = 'consumergroup="' + label(self.group) + '"'
        definitions = [
            (
                "kafka_sharegroup_exporter_scrape_success",
                "gauge",
                "Whether the last Kafka query succeeded.",
            ),
            (
                "kafka_sharegroup_exporter_last_success_timestamp_seconds",
                "gauge",
                "Unix time of the last successful Kafka query.",
            ),
            (
                "kafka_sharegroup_exporter_errors_total",
                "counter",
                "Failed Kafka offset queries.",
            ),
            (
                "kafka_sharegroup_lag",
                "gauge",
                "Share partition lag reported by Kafka; includes unfinished delivery.",
            ),
            (
                "kafka_sharegroup_start_offset",
                "gauge",
                "Share partition start offset reported by Kafka.",
            ),
            (
                "kafka_sharegroup_lag_available",
                "gauge",
                "Whether Kafka returned a lag value for this partition.",
            ),
        ]
        lines = []
        for name, kind, help_text in definitions:
            lines.extend(
                ["# HELP " + name + " " + help_text, "# TYPE " + name + " " + kind]
            )
        for name, value in [
            ("scrape_success", int(success)),
            ("last_success_timestamp_seconds", last_success),
            ("errors_total", errors),
        ]:
            lines.append(
                "kafka_sharegroup_exporter_"
                + name
                + "{"
                + group_labels
                + "} "
                + str(value)
            )
        if success:
            for topic, partition, offset, lag in rows:
                labels = (
                    group_labels
                    + ',topic="'
                    + label(topic)
                    + '",partition="'
                    + str(partition)
                    + '"'
                )
                lines.append(
                    "kafka_sharegroup_lag_available{"
                    + labels
                    + "} "
                    + str(int(lag is not None))
                )
                if lag is not None:
                    lines.append("kafka_sharegroup_lag{" + labels + "} " + str(lag))
                if offset is not None:
                    lines.append(
                        "kafka_sharegroup_start_offset{" + labels + "} " + str(offset)
                    )
        return "\n".join(lines) + "\n"


def main():
    """Start the background collector and serve metrics and liveness on port 9405."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    collector = Collector(
        os.environ["SHARE_GROUP"],
        os.environ["BOOTSTRAP_SERVERS"],
        interval=int(os.environ.get("POLL_INTERVAL_SECONDS", "30")),
        timeout=int(os.environ.get("QUERY_TIMEOUT_SECONDS", "20")),
    )
    threading.Thread(target=collector.run, daemon=True).start()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/metrics":
                body = collector.metrics().encode()
                content_type = "text/plain; version=0.0.4; charset=utf-8"
            elif self.path == "/healthz":
                body = b"ok\n"
                content_type = "text/plain"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    ThreadingHTTPServer(("0.0.0.0", 9405), Handler).serve_forever()


if __name__ == "__main__":
    main()
