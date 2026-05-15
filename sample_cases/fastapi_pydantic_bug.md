# FastAPI Pydantic Dependency Mismatch

## Case Details
Language/framework: Python, FastAPI
Environment: Local and staging startup

## Actual Behavior
API fails during startup after dependency upgrade.

## Expected Behavior
API should start and serve `/health`.

## Logs
ImportError: cannot import name 'Undefined' from 'pydantic.fields'
fastapi/dependencies/utils.py line 48

## requirements.txt
fastapi==0.95.0
pydantic==2.6.4
uvicorn==0.29.0

## Code Snippet
```py
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Ticket(BaseModel):
    title: str
```
