from __future__ import annotations

import time

from django.core.management.base import BaseCommand

from catalog.media_processing import process_next_asset_job


class Command(BaseCommand):
    help = "Process queued product and builder-item image analysis/3D jobs."

    def add_arguments(self, parser):
        parser.add_argument("--loop", action="store_true", help="Keep polling for future uploads.")
        parser.add_argument("--max-jobs", type=int, default=0, help="Stop after this many jobs; 0 means unlimited.")
        parser.add_argument("--poll-interval", type=float, default=5.0)

    def handle(self, *args, **options):
        run_forever = bool(options["loop"])
        max_jobs = max(0, int(options["max_jobs"]))
        poll_interval = max(0.5, float(options["poll_interval"]))
        processed = 0

        self.stdout.write("Asset processing worker started.")
        while True:
            job = process_next_asset_job()
            if job is not None:
                processed += 1
                self.stdout.write(f"{job.pk} {job.target_type}:{job.target_id} -> {job.status}")
                if max_jobs and processed >= max_jobs:
                    break
                continue
            if not run_forever:
                break
            time.sleep(poll_interval)

        self.stdout.write(self.style.SUCCESS(f"Processed {processed} job(s)."))
