# Reviewed baseline versus implemented coverage

Assessment `ecfdff2cf3f9d1a7b7b284e79a7f708d1baea8ce`; scans `b1e645f342be5bc84141f314a12a81d3c38f621b`. Fresh scans: **NOT RUN locally / CI PENDING**. No old artifacts were retrofitted with new bindings.

| Scan role | Production mapping | Input | Historical config SHA-256 | Historical artifact SHA-256 | New proof |
|---|---|---|---|---|---|
| backend-runtime | backend-runtime | backend/Dockerfile.runtime target=runtime | sha256:db15163e1ad8b7645c64494ffb768e142e2be8649386da23de6b6716cc1cd81d | sha256:9c237c41d0938960a8408801934537bd70e000a151ab40669dc4dfa8e7d80271 | PENDING fresh build binding + CDX/Syft/Grype + hashes |
| backend-migration | migration | backend/Dockerfile.runtime target=migration | sha256:5270f5bfd3f3ae6de537c674141d35735ab04a438b0ebe24d52da193f02ef537 | sha256:c0d5fbfd1e91e3cd795ea9d19acb08305a467ca4e19ed077707b8db98183a2f7 | PENDING fresh build binding + CDX/Syft/Grype + hashes |
| uat-backend | demo/UAT retained | backend/Dockerfile.uat | sha256:0bd355ebf3f9708de1a392c4630145781b6f76dfd0fec24f597d6562aa0fd87a | sha256:04127368f2d12dc7e1cce045c5ebc77501b0027fc7831c0d0002ebe813ae78fe | PENDING fresh build binding + CDX/Syft/Grype + hashes |
| frontend | demo/UAT retained | frontend/Dockerfile.demo | sha256:28ba17af0adb992eae0e033e918cd9f4e21b3d9c86591605a64c8309db59ba3e | sha256:de56c97035d608657ebd20dfd560b7492e4dce9399b5f026448c542b2662bf27 | PENDING fresh build binding + CDX/Syft/Grype + hashes |
| postgres | postgres-alpine | deploy/release/Dockerfile.postgres | sha256:a7d2ca3526ce25d3036f8c403504a77af1d05448708074dfaf2817f4f3be54e8 | sha256:fb7e720dbf355a8ae2dba6c68fd97fad5a5a092559c77fc6cca7b119402741f1 | PENDING fresh build binding + CDX/Syft/Grype + hashes |
| ingestion-gateway | gateway | deploy/release/Dockerfile.gateway | sha256:ba0b88987e74fdab48474cc5d4a551f54621d8649601f565bdb29b3d0aa90f04 | sha256:6ef1c70d6ce3a8be2d7eec3a93b05acc6b910abe8d9dff11c50f6bf1f91fdfc8 | PENDING fresh build binding + CDX/Syft/Grype + hashes |
| otel-contrib | contrib | otel/opentelemetry-collector-contrib:0.123.0@sha256:e39311df1f3d941923c00da79ac7ba6269124a870ee87e3c3ad24d60f8aee4d2 | sha256:f0eaa24275f0eac77186cf0c9b1d1c72c9edde884a7c6bf9e5332ca8b5939d97 | sha256:56831dd9f56a8058a56d420aef38d646e6066cd8e3d3d19d24c876cb7896de2f | PENDING fresh build binding + CDX/Syft/Grype + hashes |
| production-frontend | frontend | frontend/Dockerfile.runtime | MISSING — not assessed | MISSING | PENDING fresh build binding + CDX/Syft/Grype + hashes |

API and worker reuse backend runtime, not two independently built images. Migration is a distinct final target. The historical frontend scan covers `Dockerfile.demo`, not `Dockerfile.runtime`; the added production-frontend job closes that *contract* gap only. All six declared production roles map to eight scan roles including two retained demo/UAT roles.

## Source inventory and exclusions

Inspected all tracked Dockerfiles, Compose definitions and workflow build/pull references. Production candidate inputs are listed above. `backend/Dockerfile.demo`, root `docker-compose*.yml`, `deploy/uat/compose*.yml`, `frontend/Dockerfile.demo` and `backend/Dockerfile.uat` serve demo/development/UAT; they do not prove production readiness. `verification/dev05/{backend,frontend,browser}.Dockerfile` and its Compose are disposable tests, not additional product release artifacts. UAT publisher remains unchanged and unauthorized to run in this task. No other product-owned production Dockerfile was found. Generic external CI service containers are test infrastructure.

Final multi-architecture manifest digests, accountable release identity approval and complete frontend bundled-JavaScript licence/transitive coverage remain unresolved. Image Syft cataloguing does not prove all minified bundle dependencies are recovered. Existing component licence inventory/NOTICE review remains required. Architecture qualification is amd64 only.

## Identity contract

Independent Docker build `--iidfile` (or pinned pull inspect result) must agree with the tag at binding time. A clean committed source checkout, Dockerfile hash, target/context, role and inspected architecture are recorded. Scan runs against the config ID; CDX, Syft, Grype and provenance must all identify it. Aggregation requires all eight directories, exact event source, artifact hashes and the intended build inputs. Checksums establish consistency, not a signed build attestation. No registry publication or release identity approval is inferred.

The historical seven scans remain readable, with 984 image findings (41 Critical, 371 High, four Unknown). They do not satisfy the new binding contract and cannot be relabelled as fresh scans.
