import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from he_wsi_generator.ui.jobs import JobRunner, JobRunnerError


REPO_ROOT = Path(__file__).resolve().parents[1]


class JobRunnerTests(unittest.TestCase):
    def test_job_runner_executes_command_and_persists_completed_record(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = JobRunner(Path(tmpdir) / "jobs")

            record = runner.create_job(
                job_id="job-success",
                command=[sys.executable, "-c", "print('done')"],
            )
            completed = runner.run_job("job-success")
            persisted = json.loads(Path(completed["record_path"]).read_text(encoding="utf-8"))
            stdout = Path(completed["stdout_path"]).read_text(encoding="utf-8")

        self.assertEqual(record["status"], "queued")
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["return_code"], 0)
        self.assertEqual(persisted["status"], "completed")
        self.assertIn("done", stdout)

    def test_job_runner_marks_nonzero_command_as_failed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = JobRunner(Path(tmpdir) / "jobs")
            runner.create_job(
                job_id="job-fail",
                command=[sys.executable, "-c", "import sys; print('bad'); sys.exit(7)"],
            )

            failed = runner.run_job("job-fail")

        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["return_code"], 7)

    def test_job_runner_marks_command_launch_error_as_failed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = JobRunner(Path(tmpdir) / "jobs")
            runner.create_job(
                job_id="job-launch-error",
                command=["definitely-missing-he-wsi-generator-command"],
            )

            failed = runner.run_job("job-launch-error")
            persisted = runner.load_job("job-launch-error")
            stderr = Path(failed["stderr_path"]).read_text(encoding="utf-8")

        self.assertEqual(failed["status"], "failed")
        self.assertIsNone(failed["return_code"])
        self.assertEqual(persisted["status"], "failed")
        self.assertIn("command launch failed", failed["message"])
        self.assertIn("definitely-missing-he-wsi-generator-command", stderr)

    def test_job_runner_cancels_queued_job_and_prevents_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = JobRunner(Path(tmpdir) / "jobs")
            runner.create_job(
                job_id="job-cancel",
                command=[sys.executable, "-c", "print('should not run')"],
            )

            cancelled = runner.cancel_job("job-cancel", message="user cancelled")
            persisted = runner.load_job("job-cancel")

            with self.assertRaisesRegex(JobRunnerError, "not queued"):
                runner.run_job("job-cancel")

        self.assertEqual(cancelled["status"], "cancelled")
        self.assertEqual(persisted["status"], "cancelled")
        self.assertIsNone(cancelled["return_code"])
        self.assertEqual(cancelled["message"], "user cancelled")

    def test_job_runner_rejects_duplicate_job_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = JobRunner(Path(tmpdir) / "jobs")
            runner.create_job(
                job_id="job-001",
                command=[sys.executable, "-c", "print('one')"],
            )

            with self.assertRaisesRegex(JobRunnerError, "already exists"):
                runner.create_job(
                    job_id="job-001",
                    command=[sys.executable, "-c", "print('two')"],
                )

    def test_cli_runs_local_job(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            job_root = Path(tmpdir) / "jobs"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT / "src")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "he_wsi_generator.cli",
                    "run-local-job",
                    str(job_root),
                    "--job-id",
                    "job-cli",
                    "--",
                    sys.executable,
                    "-c",
                    "print('cli job')",
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            record = json.loads((job_root / "job-cli" / "job.json").read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("local job completed", result.stdout)
        self.assertEqual(record["status"], "completed")

    def test_cli_cancels_queued_local_job(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            job_root = Path(tmpdir) / "jobs"
            runner = JobRunner(job_root)
            runner.create_job(
                job_id="job-cli-cancel",
                command=[sys.executable, "-c", "print('should stay queued')"],
            )
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT / "src")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "he_wsi_generator.cli",
                    "cancel-local-job",
                    str(job_root),
                    "--job-id",
                    "job-cli-cancel",
                    "--message",
                    "cancelled from cli",
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            record = json.loads(
                (job_root / "job-cli-cancel" / "job.json").read_text(encoding="utf-8")
            )
            stdout = (job_root / "job-cli-cancel" / "stdout.txt").read_text(encoding="utf-8")
            stderr = (job_root / "job-cli-cancel" / "stderr.txt").read_text(encoding="utf-8")

        self.assertIn("local job cancelled", result.stdout)
        self.assertEqual(record["status"], "cancelled")
        self.assertEqual(record["message"], "cancelled from cli")
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "")

    def test_cli_rejects_cancelling_non_queued_local_job(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            job_root = Path(tmpdir) / "jobs"
            runner = JobRunner(job_root)
            runner.create_job(
                job_id="job-cli-completed",
                command=[sys.executable, "-c", "print('already done')"],
            )
            runner.run_job("job-cli-completed")
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT / "src")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "he_wsi_generator.cli",
                    "cancel-local-job",
                    str(job_root),
                    "--job-id",
                    "job-cli-completed",
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            record = json.loads(
                (job_root / "job-cli-completed" / "job.json").read_text(encoding="utf-8")
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not queued", result.stderr)
        self.assertEqual(record["status"], "completed")

    def test_cli_inspects_local_job(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            job_root = Path(tmpdir) / "jobs"
            runner = JobRunner(job_root)
            runner.create_job(
                job_id="job-inspect",
                command=[sys.executable, "-c", "print('inspect me')"],
            )
            runner.run_job("job-inspect")
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT / "src")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "he_wsi_generator.cli",
                    "inspect-local-job",
                    str(job_root),
                    "--job-id",
                    "job-inspect",
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            inspected = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(inspected["job_id"], "job-inspect")
        self.assertEqual(inspected["status"], "completed")
        self.assertIn("stdout_path", inspected)
        self.assertIn("stderr_path", inspected)

    def test_cli_rejects_inspecting_unknown_local_job(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            job_root = Path(tmpdir) / "jobs"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT / "src")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "he_wsi_generator.cli",
                    "inspect-local-job",
                    str(job_root),
                    "--job-id",
                    "missing-job",
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown job_id", result.stderr)

    def test_cli_rejects_inspecting_corrupt_local_job_record(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            job_root = Path(tmpdir) / "jobs"
            job_dir = job_root / "job-corrupt"
            job_dir.mkdir(parents=True)
            (job_dir / "job.json").write_text("{not json", encoding="utf-8")
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT / "src")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "he_wsi_generator.cli",
                    "inspect-local-job",
                    str(job_root),
                    "--job-id",
                    "job-corrupt",
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not valid JSON", result.stderr)


if __name__ == "__main__":
    unittest.main()
