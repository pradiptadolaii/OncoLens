# Render deployment preparation — not deployed

The Blueprint is a proposal, not approval to incur charges. `standard` proposes
2 GiB memory; verify current Render specifications and price and obtain owner
approval before creating any paid service. Auto-deploy is disabled. Start with
one worker. This checkout cannot currently start the real application.

## Required before deployment

1. Supply the authorized original model and establish permission to host it.
   `models/README.md` records unresolved redistribution rights and no approved
   download URL. Expected size: 44,792,971 bytes. SHA-256:
   `4ba78eaa0302a8cf35f846316888b720fbc4ce7c5ed86946b1d8fb657e0dd3a4`.
   Never substitute or retrain weights. The checkpoint is ignored by Git; copying
   it into a local checkout alone does not put it in a Render source build.
2. Choose an authorized artifact source. Prefer private artifact storage with a
   Render-only credential. Download over verified HTTPS without logging tokens,
   enforce a bounded download, verify the expected hash before atomic placement
   in `models/`, and fail the build on missing/mismatched bytes. A public Release
   requires confirmed redistribution rights. No source URL or credential is
   invented in this proposal; the current build command does not fetch weights.
3. Configure Render access securely and approve a quoted instance price. No
   Render service has been created and no hosting charges were authorized.
4. Resolve the public-access safeguards below before exposing inference.

## Validation performed locally

Python 3.11.17, CPU torch 2.14.1, torchvision 0.29.1 and the versions pinned in
requirements.txt imported successfully. Dependency compatibility, compileall,
and the existing `scripts/ci_smoke.py` passed. The latter mocks predictor
construction and does not test model loading or predictions.

Additional in-process requests with the predictor mocked verified dashboard 200,
health metadata, invalid extension/empty/invalid image 400, upload over 10 MiB
413, synthetic 224x224 acceptance, 25,005,000-pixel rejection, and
25,000,000-pixel acceptance. A mock response is not a prediction result.

Peak RSS for that validation process was 678 MiB, without model weights. The test
includes synthetic-image construction and sequential allocations, so it is not
a production worker measurement. It nevertheless shows that a 512 MiB budget
has insufficient demonstrated headroom for this workflow. Inference-module
imports alone peaked at 333.6 MiB. Measure the real service under concurrent
uploads after the authorized model arrives before finalizing the instance plan.

Actual app import failed with FileNotFoundError for the required checkpoint.
Model integrity, model loading, real prediction, real startup, Render logs and
live HTTPS remain unverified. No clinical performance claims follow from these
checks. The dashboard correctly uses same-origin /api/predict and already states
that scores are uncalibrated and the model is not clinically validated.

## Security findings and required safeguards

- No explicit application image archive or image-content logging was found.
  However Starlette's UploadFile multipart parser may spill files to temporary
  disk before endpoint validation. The current application therefore cannot
  guarantee the requested no-storage policy. Use bounded, in-memory multipart
  parsing and verify no temporary files are created before public deployment.
- The 10 MiB limit is checked after multipart parsing. Add an ingress body cap
  that counts streamed bytes, including chunked bodies and multipart overhead;
  cap files, fields and multipart headers. Content-Length checks alone do not
  provide a complete limit. Enforce size limits before buffering or parsing.
- Images are verified, dimensions capped at 25 million pixels and converted to
  RGB. Enforce actual decoded format, catch decompression-bomb failures, and
  consider a lower dimension cap to reduce memory pressure. Do not change model
  normalization, padding, class order or weights.
- Add browser-compatible authentication, such as an identity-aware access proxy
  or HTTP Basic authentication over HTTPS with credentials held only in Render
  secrets. Do not embed shared tokens in HTML. Keep health checks unauthenticated
  with minimal metadata; protect dashboard, inference, docs and schema routes.
- Add rate limits and a bounded inference queue/concurrency cap with 429/503 on
  saturation, upload/read timeouts and request monitoring without filenames,
  image contents or patient data. Synchronous inference currently blocks the
  async route; avoid an unbounded thread/worker workaround.
- No permissive CORS middleware was found; retain same-origin requests. Validate
  Origin on browser requests, add anti-framing and no-store response headers,
  and do not cache prediction responses. External fonts contact third parties;
  consider self-hosted fonts for a private research deployment.
- De-identification cannot be guaranteed by file validation. Permit only
  authorized de-identified research inputs; never upload clinical identifiers.
  Preserve the existing disclaimer and distinguish scores from calibrated
  diagnostic probabilities. The model is not clinically validated.

## Final acceptance after prerequisites are supplied

Run `sha256sum` on the actual checkpoint, real strict state-dict loading and
startup from this repository root. Start the exact Blueprint command with PORT
set and one worker. Verify GET /, GET /api/health and POST /api/predict with a
synthetic image; check all four finite scores and labels without claiming
diagnostic validity. Repeat invalid, oversized and dimension-limit requests
against the hardened server. Measure worker RSS and peak memory under bounded
concurrency. Review Render build/runtime logs with secret redaction and repeat
the checks against the actual public HTTPS URL. Record deployed Git SHA, service
ID/name, confirmed plan/price and health/prediction outcomes separately from
local tests. Do not report deployment success from a local test or open port.
