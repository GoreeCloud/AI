# GoreeCloud AI — supply-chain controls (developer preview)

These are source-level safeguards, not a certified release, complete
dependency audit, reproducible artifact, or deployment attestation.

## Current source controls

- Checkout, Python, Node and Java setup, Gradle setup, and artifact upload
  GitHub Actions are pinned to full hashes verified from their official
  GitHub repositories. Checkout credential persistence is disabled.
- The Python uv and npm package lockfiles pin resolved dependency versions.
  CI uses locked installs, pip-audit for the Python production closure and
  npm audit for web production dependencies. A clean vulnerability scan does
  not prove the dependencies secure.
- A deterministic script produces CycloneDX 1.6 **component inventories**
  from the committed lockfiles. They include development dependencies and
  third-party package names/versions; the local editable server project is
  intentionally excluded from Python third-party entries.
- Only packages from the official PyPI registry appear in the Python
  component inventory. Unknown registries cause a validation error.
- Both dependency-name-only JSON files are uploaded as GitHub CI artifacts
  with a 7-day retention. No host, model prompts, API secrets or documents
  are included. The inventory has no transitive dependency-edge guarantees.
- Hash pins reduce tag-mutation risk, but do not prove upstream source
  integrity, source-author trust, native/Gradle dependency security,
  or signed release provenance.

## Generate on a trusted development machine

    python3 tools/build_sbom.py --output dist/sbom

The generated files are dist/sbom/python.cdx.json and
dist/sbom/web.cdx.json. The dist directory is ignored by git.

Verify tests and available vulnerability advisories with:

    cd server
    uv sync --locked --extra dev --python 3.12
    uv run --locked --extra dev ruff check app tests ../tools
    uv run --locked --extra dev pytest -q
    uv export --locked --no-dev --no-emit-project --format requirements-txt -o /tmp/goreecloud-ai-deps.txt
    pip-audit -r /tmp/goreecloud-ai-deps.txt --no-deps --disable-pip

    cd ../web
    npm ci --ignore-scripts --no-audit --no-fund
    npm run build
    npm audit --omit=dev --audit-level=high

## Open release gates

- Verify transitive licenses, redistribution notices, source provenance,
  release signing and independent artifact hash checks.
- Include Android Gradle dependencies, Qt/Linux runtime wheels, native
  libraries, containers and operating-system packages in separate inventories.
- Qualify signed Android/Linux releases and reproducibility before release.
- Conduct Wardveil security assessment. Keep supply-chain validation
  separate from GoreeShield privacy, Mesh interoperability, GoreeCloud
  Identity authentication and GoreeCloud UI accessibility requirements.
