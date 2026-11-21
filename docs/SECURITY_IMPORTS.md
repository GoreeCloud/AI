# GoreeCloud AI — document parser isolation (development preview)

## Current architecture

The API accepts authenticated uploads of PDF, DOCX, TXT and Markdown, capped
at 6 MB. It does **not** parse untrusted document contents inside the FastAPI
process. A separate Python interpreter (invoked with sys.executable and -I)
handles each upload using a single-use stdin/stdout protocol on Linux.

This is a **resource-limited subprocess, not a security sandbox**.
The worker retains the host user ID, filesystem permissions and network
namespace. A parser exploit could access anything available to that identity.
Do not expose the preview to hostile uploads or production data without
Wardveil-approved stronger isolation.

## Implemented limits

| Boundary | Enforced behavior |
| --- | --- |
| API access | Owner bearer token or configured signed JWT owner mode |
| Upload | 6,000,000 bytes maximum; supported extensions only |
| Process | New Linux Python process per upload, isolated -I interpreter |
| Environment | Only LANG and PYTHONNOUSERSITE; no API/model tokens forwarded |
| Wall time | 10 seconds by API; kill and wait on timeout or cancellation |
| Import concurrency | At most 2 simultaneous subprocesses per API worker; excess requests return HTTP 429 |
| CPU time | Linux RLIMIT_CPU 6 soft/7 hard seconds |
| Virtual memory | Linux RLIMIT_AS 512 MiB |
| Other limits | No core dumps; 64 file descriptors |
| DOCX zip | 500 members, 25 MB *declared* expansion, reject encrypted/unsupported zip members |
| PDF | 100 pages maximum; encrypted PDFs refused |
| Text output | 250,000 characters maximum with truncation flag |
| IPC output | 1,200,000-byte limit before decoding structured JSON |
| Errors | No parser tracebacks, extracted text or secret values in HTTP errors |

## Threats not solved

- No seccomp profile, filesystem jail, container, network-egress denial,
  dedicated unprivileged user, malware scanner, credential broker or
  permission separation. Real sandboxing remains a P0 release gate.
- Uploaded multipart bytes and live SQLite documents are not encrypted.
  Temporary file spooling and host backups may retain sensitive information.
- PDF/DOCX embedded links and text are untrusted data, never permissions,
  system instructions or evidence that an agent action was approved.
- A two-slot semaphore bounds local API worker concurrency, but it does not
  coordinate across multiple Uvicorn processes/replicas or ingress sites.
  Host resource exhaustion remains possible; add global worker/cgroup quotas,
  backpressure and ingress rate limits before exposing the API publicly.

## Regression verification

On a trusted Linux development host using locked dependencies:

    cd server
    uv run --locked --extra dev ruff check app tests
    uv run --locked --extra dev pytest -q tests/test_extract_worker.py
    uv run --locked --extra dev pytest -q

Tests cover valid text/DOCX/PDF, malformed input, existing DOCX decompression
limit, owner authentication, sanitized process environment, timeout termination,
bounded worker output and cancellation cleanup. No provider calls or real
private documents are necessary.

## Next release gates

1. Run worker as a separate non-privileged UID inside a network-denied OS
   sandbox with read-only mounts and strict cgroup/process limits.
2. Add per-owner import concurrency limits, parser fuzzing, malware inspection
   where appropriate and file-MIME verification.
3. Test real Linux containers, device imports, recovery and ingress limits.
4. Enforce verified GoreeShield privacy and Wardveil cybersecurity controls,
   plus distinct GoreeCloud Identity and Mesh contracts.
