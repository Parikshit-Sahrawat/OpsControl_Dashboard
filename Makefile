SHELL := /bin/bash
.PHONY: test test-unit test-integration test-e2e test-agent test-security test-all test-quality test-coverage test-performance test-docker test-compatibility

test: test-unit

test-unit:
	bash scripts/test-quality.sh unit

test-integration:
	bash scripts/test-quality.sh integration

test-e2e:
	bash scripts/test-quality.sh e2e

test-agent:
	bash scripts/test-quality.sh agent

test-security:
	bash scripts/test-quality.sh security

test-quality:
	bash scripts/test-quality.sh quality

test-coverage:
	bash scripts/test-quality.sh coverage

test-performance:
	bash scripts/test-quality.sh performance

test-docker:
	bash scripts/test-quality.sh docker

test-all:
	bash scripts/test-quality.sh all

test-compatibility:
	bash scripts/test-quality.sh compatibility

.PHONY: test-pipeline-v16
test-pipeline-v16:
	cd backend && ENV=test .venv/bin/python -m unittest discover -s tests -p 'test_pipeline_transport_v16.py' -v
	V16_API_ACCEPTANCE=1 backend/.venv/bin/python scripts/v16-acceptance.py
