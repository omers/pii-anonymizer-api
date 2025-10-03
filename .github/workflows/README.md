# GitHub Actions CI/CD Workflows

This directory contains GitHub Actions workflows for the PII Anonymizer API project.

## 🔄 Workflows Overview

### 1. CI - Test Suite (`ci.yml`)
**Main testing workflow that runs on every push and pull request**

#### Features:
- **Multi-Python Testing**: Tests across Python 3.9, 3.10, 3.11, and 3.12
- **Cross-Platform**: Tests on Ubuntu, macOS, and Windows
- **Comprehensive Testing**:
  - Unit tests with pytest
  - Integration tests
  - Performance tests
  - Simple functionality tests
- **Code Quality Checks**:
  - Linting with flake8
  - Type checking with mypy
  - Code formatting with black
  - Import sorting with isort
- **Security Scanning**:
  - Dependency vulnerability scanning with safety
  - Static code analysis with bandit
- **Coverage Reporting**:
  - Detailed coverage reports
  - HTML coverage reports
  - Codecov integration

#### Test Matrix:
| OS | Python Versions |
|---|---|
| Ubuntu | 3.9, 3.10, 3.11, 3.12 |
| macOS | 3.11 |
| Windows | 3.11 |

### 2. Test Report & Coverage (`test-report.yml`)
**Enhanced reporting workflow that runs after the main CI**

#### Features:
- **Detailed Test Reports**: Publishes comprehensive test results
- **Coverage Comments**: Adds coverage reports to PR comments
- **Performance Summaries**: Shows benchmark results
- **Status Notifications**: Provides clear CI status summaries

## 🚀 What Runs When

### On Push to `main` or `develop`:
1. Full test suite across all Python versions
2. Code quality checks
3. Security scans
4. Coverage reporting
5. Performance benchmarks

### On Pull Requests:
1. Same as push triggers
2. **Plus**: Enhanced PR comments with:
   - Test results summary
   - Coverage reports
   - Performance metrics
   - Code quality feedback

### Manual Triggers:
- Both workflows can be triggered manually via GitHub Actions UI

## 📊 Test Categories

The test suite is organized into categories using pytest markers:

- **`unit`**: Fast, isolated unit tests
- **`integration`**: End-to-end API functionality tests
- **`performance`**: Load testing and response time validation
- **`slow`**: Tests that take longer to run

## 🎯 Coverage Goals

- **Target Coverage**: 80%+
- **Coverage Reports**: Generated in multiple formats (XML, HTML, terminal)
- **Coverage Tracking**: Integrated with Codecov for trend analysis

## 🔧 Optimization Features

### Dependency Caching
- Smart pip dependency caching based on `requirements.txt` hash
- Reduces build time by caching Python packages

### Parallel Execution
- Tests run in parallel across different Python versions
- Security and quality checks run independently

### Fail-Fast Strategy
- Disabled to ensure all combinations are tested
- Individual failures don't stop the entire matrix

## 📝 Test Reporting

### What You'll See:
1. **GitHub Checks**: Test status directly in PR/commit view
2. **PR Comments**: Detailed coverage and performance reports
3. **Artifacts**: Downloadable test reports and coverage files
4. **Codecov**: Trend analysis and coverage visualization

### Test Output Includes:
- ✅ Pass/fail status for each test category
- 📊 Coverage percentages and missing lines
- 🚀 Performance metrics and timing
- 🔍 Code quality scores
- 🛡️ Security scan results

## 🛠️ Local Testing

To run the same tests locally:

```bash
# Install dependencies
make install

# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test categories
make test-unit
make test-integration
make test-performance

# Code quality checks
make lint
make format
```

## 🔐 Security Features

- **Dependency Scanning**: Checks for known vulnerabilities
- **Static Analysis**: Identifies potential security issues
- **No Secrets in Logs**: Careful handling of sensitive data
- **Minimal Permissions**: Workflows use least-privilege access

## 📈 Performance Monitoring

- **Response Time Tracking**: API endpoint performance
- **Memory Usage**: Resource consumption monitoring
- **Load Testing**: Concurrent request handling
- **Regression Detection**: Performance degradation alerts

## 🎨 Customization

### Adding New Test Categories:
1. Add pytest marker in `pytest.ini`
2. Update `conftest.py` with marker definition
3. Add step in `ci.yml` workflow

### Modifying Coverage Thresholds:
- Update `--cov-fail-under` in `pytest.ini`
- Adjust thresholds in `test-report.yml`

### Adding New Python Versions:
- Update matrix in `ci.yml`
- Ensure compatibility in `requirements.txt`

## 🚦 Status Badges

Add these to your README for quick status visibility:

```markdown
![CI](https://github.com/yourusername/pii-anonymizer-api/workflows/CI%20-%20Test%20Suite/badge.svg)
![Coverage](https://codecov.io/gh/yourusername/pii-anonymizer-api/branch/main/graph/badge.svg)
```

## 🔧 Troubleshooting

### Common Issues:

1. **SpaCy Model Installation Fails**:
   - Workflow continues with `continue-on-error: true`
   - Check `scripts/install_spacy_model.py` for issues

2. **Coverage Below Threshold**:
   - Review uncovered lines in HTML report
   - Add tests for missing coverage

3. **Dependency Conflicts**:
   - Check `scripts/check_dependencies.py` output
   - Update `requirements.txt` versions

4. **Platform-Specific Failures**:
   - Review OS-specific test results
   - Use platform-specific skips if needed

---

*This CI setup provides comprehensive testing while maintaining fast feedback loops and detailed reporting.*

