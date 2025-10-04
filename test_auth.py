#!/usr/bin/env python3

import pytest
from fastapi.security import HTTPBearer
from fastapi import Request, HTTPException

@pytest.mark.asyncio
async def test_auth():
    hb = HTTPBearer()
    
    # Create a mock request without Authorization header
    scope = {
        'type': 'http',
        'method': 'POST',
        'url': 'http://test',
        'headers': []
    }
    req = Request(scope, None)
    
    try:
        result = await hb(req)
        print('Result:', result)
    except HTTPException as e:
        print('HTTPException:', e.status_code, e.detail)
    except Exception as e:
        print('Other exception:', type(e).__name__, str(e))

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_auth())
