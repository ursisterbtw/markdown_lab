# Create and activate Python virtual environment
Write-Host "Creating Python virtual environment..." -ForegroundColor Green
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install Python dependencies
Write-Host "Installing Python dependencies..." -ForegroundColor Green
python -m pip install --upgrade pip
python -m pip install -r scripts/requirements.txt

# Generate visualizations
Write-Host "Generating benchmark visualizations..." -ForegroundColor Green
python scripts/visualize_benchmarks.py

# Open the results in the default browser
Write-Host "Opening benchmark results..." -ForegroundColor Green
Start-Process "target/criterion/benchmark_results.html"

# Deactivate virtual environment
deactivate

Write-Host "Done! Benchmark results are available in target/criterion/benchmark_results.html" -ForegroundColor Green
