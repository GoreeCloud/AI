# GoreeCloud AI — document parser isolation (development preview)

## Current architecture

The API accepts authenticated uploads of PDF, DOCX, TXT and Markdown, capped
at 6 MB. A bounded **preflight** inspects only the supplied bytes' PDF 1.x/2.x
header, ZIP local-file signature for DOCX and valid UTF-8 without NUL for
plain text/Markdown. Obvious mislabeling is rejected with a generic HTTP 422
before subprocess creation. This does **not** prove the file is safe, validate
its complete MIME structure or detect malware. The API does **not** parse
PDF/DOCX structure in the web process; the existing separate interpreter
(invoked with sys.executable and -I) handles full parsing under resource limits
using a single-use stdin/stdout protocol on Linux.

Two operator-selectable Linux import modes now exist. The backward-compatible
default, **process**, keeps the original limited worker running under the host
UID and namespaces; it is **not a sandbox**. Opting into **bwrap** requires an
installed, root-owned, non-group/world-writable Bubblewrap executable. In that
mode each worker runs in a fresh unshared user/PID/network/IPC/mount namespace
with the Python runtime and parser script mounted read-only, isolated /tmp and
no host HOME or data-directory mount. The service supplies only synthetic
runtime variables, not API/model tokens. Failure to construct or start a
requested bwrap sandbox is **not silently downgraded** to process mode.

This is a tested OS-level isolation *mechanism*, not comprehensive Wardveil
security acceptance. The process still uses the configured service's host UID
outside its namespace; no seccomp policy, separate host UID, cgroup isolation,
image malware inspection or independent penetration assessment is provided.
Do not expose the preview publicly or handle hostile private uploads before
production configuration and qualification.

## Implemented limits

| Boundary | Enforced behavior |
| --- | --- |
| API access | Owner bearer token or configured signed JWT owner mode |
| Upload | 6,000,000 bytes maximum; supported extensions, PDF/ZIP magic-byte and UTF-8/plain-text preflight before parser spawn |
| Process | New Linux Python process per upload, isolated -I interpreter |
| Optional Bubblewrap | GOREECLOUD_AI_IMPORT_ISOLATION=bwrap; namespace, read-only runtime, no network, isolated /tmp, no private host filesystem binds |
| No downgrade | Missing or invalid sandbox binary refuses import; process mode is deliberate default only |
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

- Default process mode retains host filesystem and network. Optional bwrap
  blocks those via namespaces and read-only mounts but is still not
  independently reviewed. There is no seccomp policy, dedicated host UID,
  cgroup limit, malware scanner or secret broker. Further isolation, reliable
  environment-specific verification and Wardveil acceptance remain open.
- Multipart uploads may spool unencrypted temporary file bytes; live
  SQLite documents use plaintext storage **unless** optional SQLCipher mode
  is correctly enabled with external key custody. Older backups, swap,
  plaintext export files and old databases may retain sensitive information.
- PDF/DOCX embedded links and text are untrusted data, never permissions,
  system instructions or evidence that an agent action was approved.
- A two-slot semaphore bounds local API worker concurrency, but it does not
  coordinate across multiple Uvicorn processes/replicas or ingress sites.
  Host resource exhaustion remains possible; add global worker/cgroup quotas,
  backpressure and ingress rate limits before exposing the API publicly.

## Runtime selection and regression verification

Use GOREECLOUD_AI_IMPORT_ISOLATION=process for backwards-compatible trusted
development only, or bwrap on a Linux host where the root-owned Bubblewrap
binary supports user/mount/network namespaces. Set
GOREECLOUD_AI_BWRAP_PATH to a trusted, non-symlink, absolute executable path
only if the system default cannot be found. Do not install or run a random
unverified sandbox binary. Sandbox failures refuse the document upload rather
than falling back automatically. Validate locally with **synthetic** inputs
before choosing the stricter mode; don't rely on configuration alone.

On a trusted Linux development host using locked dependencies:

    cd server
    uv run --locked --extra dev ruff check app tests
    uv run --locked --extra dev pytest -q tests/test_extract_worker.py
    uv run --locked --extra dev pytest -q tests/test_import_sandbox.py
    uv run --locked --extra dev pytest -q

Tests cover authenticated PDF/DOCX/text/Markdown preflight (including real
synthetic files, invalid signatures, UTF-8/BOM and binary rejection before
worker creation), valid text/DOCX/PDF parsing, existing DOCX decompression
limit, owner authentication, sanitized process environment, timeout termination,
bounded worker output and cancellation cleanup. On Linux hosts where Bubblewrap
can actually enter unprivileged namespaces, synthetic integration tests check
file, environment and network isolation. Hosted CI that has the binary but
denies user namespaces records these runtime tests as **skipped**, not passed;
no production safety is inferred from the skipped checks. No provider calls
or real private documents are necessary.

## Next release gates

1. Require the verified bwrap mode for exposed deployments and validate the
   exact kernel/host/container behavior; add a dedicated unprivileged host
   UID, seccomp profile and strict cgroup/process limits.
2. Add per-owner import concurrency limits, parser fuzzing, malware inspection
   where appropriate and file-MIME verification.
3. Test real Linux containers, device imports, recovery and ingress limits.
4. Enforce verified GoreeShield privacy and Wardveil cybersecurity controls,
   plus distinct GoreeCloud Identity and Mesh contracts.
