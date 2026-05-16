# Runtime Runs

Use this folder for run-scoped metadata and resumable records for `build_master_crawler`.

Examples:
- one folder per major run attempt
- checkpoint metadata for resumable work
- links or notes that connect a run to outputs and logs
- run artifacts that need to survive terminal interruption

If a run needs to be resumed later, this folder should contain the minimum context required to restart cleanly.
