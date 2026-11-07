.PHONY: install test lint demo schemas serve

install:
	python3 -m pip install -e ".[dev,triton,recomputation-research]" --break-system-packages

test:
	python3 -m pytest -v

lint:
	python3 -m ruff check .

demo:
	python3 examples/local-demo/run_demo.py

schemas:
	python3 -c "import json; from frontier_verify.evidence.models import Evidence; from frontier_verify.receipts.models import Receipt; from frontier_verify.policies.models import Policy; json.dump(Evidence.model_json_schema(), open('schemas/evidence.schema.json','w'), indent=2); json.dump(Receipt.model_json_schema(), open('schemas/receipt.schema.json','w'), indent=2); json.dump(Policy.model_json_schema(), open('schemas/policy.schema.json','w'), indent=2)"

serve:
	uvicorn frontier_verify.api.main:app --reload --host 127.0.0.1 --port 8000
