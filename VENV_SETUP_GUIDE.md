# Virtual Environment Setup Guide

## Problem
Your terminal is using the system pytest (7.4.0) instead of your virtual environment's pytest (8.4.1).

## Solution Steps

### Step 1: Check Your Current Environment
```bash
# Check which Python you're using
which python
python --version

# Check which pytest you're using  
which pytest
pytest --version

# Check if you're in a virtual environment
echo $VIRTUAL_ENV
```

### Step 2: Locate Your Virtual Environment

#### If using venv:
```bash
# Common locations for venv
ls -la ~/.virtualenvs/
ls -la ./venv/
ls -la ./env/
```

#### If using conda:
```bash
conda env list
conda info --envs
```

#### If using pyenv:
```bash
pyenv versions
pyenv which python
```

### Step 3: Activate Your Virtual Environment

#### For venv:
```bash
# If venv is in current directory
source venv/bin/activate

# If venv is elsewhere (replace path)
source /path/to/your/venv/bin/activate
```

#### For conda:
```bash
# Replace 'your_env_name' with actual environment name
conda activate your_env_name
```

#### For pyenv:
```bash
# Set local Python version for this project
pyenv local your_python_version
```

### Step 4: Verify Activation
After activation, you should see:
```bash
# Your prompt should show (venv_name) or similar
(your_env) $ 

# These should point to your virtual environment
which python
which pip
which pytest

# Should show pytest 8.4.1
pytest --version
```

### Step 5: Install Dependencies in Virtual Environment
```bash
# Make sure you're in the day_trade_assistant directory
cd /Users/nguyenbv/rongxanh88/integrated_ai_practice/day_trade_assistant

# Install/upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Verify pytest version
pytest --version
```

### Step 6: Run Tests
```bash
# Run all tests
pytest tests/test_tradier_client_historical.py -v

# Run specific test
pytest tests/test_tradier_client_historical.py::TestTradierClientHistorical::test_get_historical_data_basic -v
```

## Common Issues & Solutions

### Issue 1: "pytest: command not found"
```bash
# Install pytest in your virtual environment
pip install pytest pytest-asyncio

# Or use python -m pytest
python -m pytest tests/test_tradier_client_historical.py -v
```

### Issue 2: Virtual environment not found
```bash
# Create a new virtual environment
python -m venv venv

# Activate it
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### Issue 3: Wrong Python version
```bash
# Check available Python versions
python3 --version
python3.9 --version  # try different versions

# Create venv with specific Python
python3.9 -m venv venv
```

### Issue 4: PowerShell on Windows/Mac
```powershell
# For PowerShell, use different activation
venv\Scripts\Activate.ps1

# Or
.\venv\Scripts\Activate.ps1
```

## Alternative: Use python -m pytest
If you can't get pytest directly, you can always use:
```bash
python -m pytest tests/test_tradier_client_historical.py -v
```

## Quick Test
To test if everything is working:
```bash
python -c "import pytest; print(pytest.__version__)"
python -c "import vcr; print('VCR available')"
python -c "import httpx; print('httpx available')"
```

## Environment Variables
Don't forget to set your Tradier API key:
```bash
# Create .env file
echo "TRADIER_API_ACCESS_TOKEN=your_api_key_here" > .env

# Or export directly
export TRADIER_API_ACCESS_TOKEN=your_api_key_here
``` 