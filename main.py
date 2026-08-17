from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Request, status, HTTPException
from math import floor

app = FastAPI()

token_buckets: dict[str, (int, datetime)] = {}
BUCKET_SIZE = 10
RATE_LIMIT = 1

@app.get("/")
async def root():
    return {"message": "Hello, World!"}

@app.get("/unlimited")
async def unlimited_requests():
    return "hello, I'm unlimited"

@app.get("/limited")
async def limited_reqs(request: Request):
    ip_addr = request.client.host
    # grab the ip address of the client sending the request using the request object
    """
    If the IP address exists in the dictionary, 
    then determine number of new tokens to add(make sure it doesn't go over bucket size)
    remove a single token if there are sufficient token
    """
   
    if ip_addr in token_buckets: 
        # calculate new tokens
        current_token_count: int = token_buckets.get(ip_addr)[0]
        last_request_received: datetime = token_buckets.get(ip_addr)[1]
        add_tokens = RATE_LIMIT * floor((datetime.now() - last_request_received).seconds)
        # refill the bucket with accumulated tokens
        if current_token_count + add_tokens >= BUCKET_SIZE:
            current_token_count = 10
        if current_token_count + add_tokens < BUCKET_SIZE:
            current_token_count += add_tokens
        # take a single token from current count, to let this current request pass through
        if current_token_count >= 1:
            current_token_count -= 1
        else:
            #update the last received request time and then return the exception
            token_buckets[ip_addr] = (current_token_count, datetime.now())
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests received. Please try again later.",
                headers={"Retry-After": "60"}
            )
        # update the last received request time
        token_buckets[ip_addr] = (current_token_count, datetime.now())
        return {
            "message": 'Success. Request was received!'
        }
    else:
        # Initialize bucket and current request time in the dict
        # remove a single token for this request
        token_buckets[ip_addr] = (BUCKET_SIZE - 1, datetime.now())
        return {
            "message": 'Success. Request was received!'
        } 




       
