PY ?= python3
CORPUS_URL := https://raw.githubusercontent.com/karpathy/char-rnn/master/data/tinyshakespeare/input.txt

.PHONY: quickstart test clean

shakespeare.txt:
	curl -sSL -o $@ $(CORPUS_URL)

# Train the toy models and LoRA adapters (about 30 seconds on one CPU core).
.artifacts: shakespeare.txt train.py train_variants.py lora.py model.py
	$(PY) train.py
	$(PY) train_variants.py
	$(PY) lora.py
	@touch $@

# Run the experiment suite that produces test_suite_results.json.
quickstart: .artifacts
	$(PY) test_suite.py

# Reproduce, then assert the README's headline findings.
test: quickstart
	$(PY) -m pytest -q tests

clean:
	rm -f .artifacts shakespeare.txt
