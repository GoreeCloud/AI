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
  from committed Python/npm lockfiles plus explicit direct Android Gradle
  source declarations. Lock inventories include development dependencies and
  names/versions; local editable Python source is excluded from third-party
  entries. Android `android-direct.cdx.json` lists only declared direct Maven
  coordinates and Gradle plugin **IDs**, not the resolved plugin artifact or
  transitive Gradle graph. No native library/license completeness is implied.
- Only packages from the official PyPI registry appear in the Python
  component inventory. Unknown registries cause a validation error.
- Source-derived Python/npm/Android direct-declaration inventories are uploaded
  as a GitHub CI artifact with 7-day retention. The Linux Qt CI job also
  generates and uploads a **separate partial inventory** of installed PySide6
  Python wheel versions from its actual CI runtime (`--include-qt-runtime`);
  it is not a lock or Qt C++/OS dependency graph and may vary by resolution.
  No host, model prompts, API secrets or documents are included. Neither
  artifact has complete dependency-edge or provenance guarantees.
- Hash pins reduce tag-mutation risk, but do not prove upstream source
  integrity, source-author trust, native/Gradle dependency security,
  or signed release provenance.

## Generate on a trusted development machine

    python3 tools/build_sbom.py --output dist/sbom

The script normally generates:
`dist/sbom/python.cdx.json`, `dist/sbom/web.cdx.json` and
`dist/sbom/android-direct.cdx.json`. The Android inventory contains
the pinned direct dependencies in both application and pinned GoreeCloud UI
Gradle build declarations (test-only JUnit marked excluded). Plugin IDs are
recorded as generic source declarations, **not fabricated Maven artifacts**.
Generate the partial selected PySide6 wheel inventory only after installing a
trusted Qt Python runtime on the intended host:

    python3 tools/build_sbom.py --output dist/sbom --include-qt-runtime

The optional `qt-runtime.cdx.json` records installed PySide6-family Python
wheels, not Qt plugins, OS libraries, native DLLs/ELFs or license attestations.
The dist directory is ignored by git.

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
- Obtain actual **resolved** Android Gradle transitive and build-plugin
  graphs with artifact hashes, verification metadata and licenses (the new
  source-only direct declarations are not enough). Include complete
  Qt/Linux native plugins, OS libraries, containers and operating-system
  packages; CI PySide6 wheel inventory is only a partial first step.
- Qualify signed Android/Linux releases and reproducibility before release.
- Conduct Wardveil security assessment. Keep supply-chain validation
  separate from GoreeShield privacy, Mesh interoperability, GoreeCloud
  Identity authentication and GoreeCloud UI accessibility requirements.
