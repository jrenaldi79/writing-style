# Writing Style Clone - Test Suite

Comprehensive unit and integration tests for the v2 preprocessing pipeline.

## Test Coverage

### Unit Tests

#### `test_filter_emails.py` (164 lines)
Tests email quality filtering:
- ✅ Valid emails pass (executive briefs, client responses)
- ✅ Invalid emails rejected (forwards, auto-replies, too short, mass emails)
- ✅ Quality score computation (length, originality, diversity)
- ✅ Body extraction and text cleanup
- ✅ Deterministic filtering (same input = same output)

#### `test_enrich_emails.py` (238 lines)
Tests metadata enrichment:
- ✅ Recipient classification (individual, small_group, team, broadcast)
- ✅ Audience detection (internal, external, mixed)
- ✅ Thread position detection (initiating, reply, forward)
- ✅ Time context extraction (time of day, weekend detection)
- ✅ Structure analysis (bullets, paragraphs, greeting, closing)
- ✅ Deterministic enrichment

#### `test_clustering.py` (255 lines)
Tests embedding and clustering:
- ✅ Model loading (sentence-transformers)
- ✅ Embedding generation (384-dim vectors)
- ✅ Deterministic embeddings
- ✅ Similarity for related texts
- ✅ K-Means clustering
- ✅ Silhouette scoring
- ✅ Calibration file validation
- ✅ Batch JSON schema validation

### Integration Tests

#### `test_integration.py` (268 lines)
Tests end-to-end workflows:
- ✅ Filter → Enrich pipeline
- ✅ Invalid emails blocked before enrichment
- ✅ All valid samples pass through pipeline
- ✅ Batch JSON structure compliance
- ✅ Persona consistency in batches
- ✅ Data preservation across stages
- ✅ Metadata accumulation

## Running Tests

### All Tests
```bash
cd /Users/john_renaldi/writing-style/tests
python run_tests.py
```

### Specific Test File
```bash
python test_filter_emails.py
python test_enrich_emails.py
python test_clustering.py
python test_integration.py
```

### Quiet Mode
```bash
python run_tests.py --quiet
```

### Individual Test Class
```bash
python -m unittest test_filter_emails.TestEmailFiltering
```

### Individual Test Method
```bash
python -m unittest test_filter_emails.TestEmailFiltering.test_filter_executive_brief_passes
```

## Prerequisites

### Required
```bash
pip install sentence-transformers scikit-learn numpy
```

### Optional (for full clustering tests)
```bash
pip install hdbscan
```

## Test Fixtures

`test_fixtures.py` provides sample emails in Gmail API format:

| Fixture | Type | Should Pass Filtering |
|---------|------|-----------------------|
| `executive_brief` | Team update | ✅ Yes |
| `client_response` | Client email | ✅ Yes |
| `quick_reply` | Short reply | ✅ Yes |
| `forward` | Forwarded email | ❌ No |
| `auto_reply` | Out of office | ❌ No |
| `too_short` | "Thanks!" | ❌ No |
| `mass_email` | 25+ recipients | ❌ No |

## Expected Results

With all dependencies installed:

```
Test Summary:
- Tests run: 40+
- Successes: 40+
- Failures: 0
- Errors: 0
- Skipped: 0-5 (if sentence-transformers not installed)
```

## Skipped Tests

Some tests are skipped if dependencies are missing:

| Test | Requires | Skip Reason |
|------|----------|-------------|
| `test_model_loads` | sentence-transformers | Model download |
| `test_embedding_*` | sentence-transformers | Embedding generation |
| `test_kmeans_clustering` | scikit-learn | Clustering algorithms |

Install missing dependencies to enable skipped tests.

## Adding New Tests

1. Create `test_<module>.py` in this directory
2. Import from `test_fixtures.py` for sample data
3. Follow existing test patterns
4. Run `python run_tests.py` to verify

### Example Test Structure

```python
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "skill" / "scripts"))

from test_fixtures import get_sample_email
import my_module

class TestMyFeature(unittest.TestCase):
    def test_something(self):
        email = get_sample_email("executive_brief")
        result = my_module.process(email)
        self.assertEqual(result, expected_value)

if __name__ == '__main__':
    unittest.main()
```

## Continuous Integration

To run tests in CI:

```yaml
# .github/workflows/test.yml
name: Test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.8'
      - run: pip install -r requirements.txt
      - run: cd tests && python run_tests.py
```

## Test Philosophy

1. **Unit tests** verify individual functions work correctly
2. **Integration tests** verify components work together
3. **Fixtures** provide realistic sample data
4. **Determinism** same input always produces same output
5. **Coverage** test both happy paths and edge cases

## Known Limitations

- Tests use sample emails, not real Gmail API responses
- Model download tests may be slow on first run
- Some tests skip if optional dependencies missing
- Validation tests require LLM API (not included)

## Debugging Failed Tests

### View detailed output
```bash
python -m unittest -v test_filter_emails.TestEmailFiltering.test_filter_executive_brief_passes
```

### Use Python debugger
```python
import pdb; pdb.set_trace()  # Add to test
```

### Check fixtures
```bash
python -c "from test_fixtures import get_sample_email; print(get_sample_email('executive_brief'))"
```
