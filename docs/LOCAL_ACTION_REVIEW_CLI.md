# GoreeCloud AI — Local Action Review CLI (Development)

This is a local, non-executing workflow for inspecting a proposed action from an installed Ollama model. It does **not** connect to the named provider, create permissions, issue user consent, or reserve an action. It is not a deployed Glaze screen.

## Usage

Create a locally reviewed manifest and obtain its SHA-256 from a separately trusted operator source. Write the exact target to a private file instead of supplying it as a shell argument:

```sh
printf '%s' 'list:sample' > ./target.txt

printf '%s' 'List two items' | python3 scripts/ai_review_local.py \
  --manifest ./reviewed-manifest.json \
  --sha256 YOUR_INDEPENDENTLY_VERIFIED_SHA256 \
  --model YOUR_INSTALLED_OLLAMA_MODEL \
  --transport mcp \
  --operation items.read \
  --field count:integer \
  --target-file ./target.txt > ./review.html
```

Open `review.html` on your local device. Output format defaults to responsive, script-free HTML with semantic labels, accessible status, light/dark styling, and escaped resource/argument text. Pass `--format json` to emit the same review data as JSON. All content may contain sensitive user data: keep the target file and output private, avoid sharing them, and remove temporary files when no longer needed. Redirecting stdout to disk persists the review; the CLI itself does not write an output file.

The `--field` option is an explicit **development-only input contract** supporting `string`, `integer`, `boolean`, and `string_list` (up to 64 bounded strings). Fields are required by default; suffix `:optional` permits absence, not an incorrect type. For example, `--field count:integer --field tags:string_list:optional` accepts `{ "count": 2 }` or `{ "count": 2, "tags": ["urgent"] }`. Invalid, missing required, extra, duplicate, incorrectly typed, oversized, or changed arguments fail closed; the canonical argument digest is checked again before review. Fields are operator-reviewed contract declarations, never model-generated schemas. The target must match the model-proposed resource exactly. Manifests and targets are read with size limits and checked before generating a proposal. The supplied `--sha256` must be independently authenticated; accepting a manifest and digest from the same untrusted provider is insufficient.

The directory uses a synthetic `local-preview` connection; `--operation` is a preview allowlist, not a real user's service grant. The model gateway accepts only trusted HTTP loopback endpoints and refuses Ollama tool calls. Shell arguments and terminal redirection can still be visible to local processes or operators; private data must be handled accordingly.

## Trust boundary and verification

The review view contains **no Approve button**, local HTTP authorization endpoint, hidden form, JavaScript, live connector, or credential handling. Any future Glaze approval experience needs actual authenticated Identity/Policy/consent issuance, exact tenant and target scoping, one-time approval with cancellation and expiry, replay and idempotency, real connector sandboxing and security acceptance.

`scripts/test_ai_review_local.py` verifies the CLI with a synthetic loopback Ollama server and checks bad digest/field denial, actual HTML/JSON review output, target mismatch denial, and absence of tool calls. This does not prove that a real Ollama model or provider is available. The existing review-lifecycle tests cover escaped hostile text, mutation isolation, approval and replay denial.

## Private-file export without overwriting

Use `--output ./review.html` (or `--format json --output ./review.json`)
to save a new local review file without printing its sensitive contents to
standard output. The tool stages output in the same directory as the target,
flushes it to disk, and publishes the file with a no-replace hard link.
Staged files are created with owner-only `0600` permissions on POSIX
systems. An existing destination, including a symbolic link, is refused;
retries must select a new filename. Errors do not print raw arguments,
resources, or the destination path. A brief non-sensitive completion notice
appears on stderr.

The directory and filesystem still require appropriate local permissions
and encryption. Explicit export **persists user/model-supplied data**; secure
storage, retention, backups and deletion are the operator's responsibility.
The default remains stdout-only for backwards compatibility. An absolute
path is not required; the user selects the intended local output location.
The export does not approve, reserve or execute any action.
