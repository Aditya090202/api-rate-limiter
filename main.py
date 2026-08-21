from datetime import datetime, timezone, timedelta
from ipaddress import ip_address
from fastapi import FastAPI, HTTPException, Request, status, HTTPException
from math import floor
import time

app = FastAPI()

token_buckets: dict[str, (int, datetime)] = {}
fixed_window_dict: dict[str, (int, int)] = {}
sliding_window_log:dict[str, list[datetime]] = {}
SLIDING_WINDOW_INTERVAL = 60 
INTERVAL_SIZE_IN_SECONDS = 60
THRESHOLD_PER_INTERVAL = 10
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

@app.get("/fixed-window-counter")
async def fixed_window(req:Request):
    """
    Choose an interval (1 second, 1 minute, 1 hour)
    Keep track of the number of requests that have arrived within this interval using a counter
    if the number of request exceed a set threshold, then throw away any extra requests after that interval
    """
    # grab the id for this request
    id_for_request = floor(time.time() / INTERVAL_SIZE_IN_SECONDS)
    # grab the ip address to use if this request is not yet added to the dict
    ip_addr = req.client.host
    # check if the ip address of this request exists in the dict
    # means we have gotten requests from this ip before and it should be in the dict as a result
    if ip_addr in fixed_window_dict:
        # grab the current id and the number of requests in this interval and store their copies in variables
        current_id: int = fixed_window_dict.get(ip_addr)[1]
        current_num_of_requests: int = fixed_window_dict.get(ip_addr)[0]
        # check if the current request has the same id (meaning it is still in the same interval)
        # if yes, then increment the number of requests and keep the id same
        if current_id == id_for_request:
            if current_num_of_requests + 1 > THRESHOLD_PER_INTERVAL:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests received. Please try again later.",
                    headers={"Retry-After": "60"}
                )
            current_num_of_requests +=1 
            fixed_window_dict[ip_addr] = (current_num_of_requests, current_id)
            return {
                "message": "Request went through successfully!"
            }
       
        # if not then reset the number of requests and assign it the new id
        fixed_window_dict[ip_addr] = (0, id_for_request)
        return {
                "message": "Request went through successfully!"
            }

    # if the ip address is not added to the dictionary, then add it (this is a new request from a new ip address)
    else:
        fixed_window_dict[ip_addr] = (1, id_for_request)
        return {
            "message": "Request went through successfully!"
        }
         
    
@app.get("/sliding-window-log")
async def sliding_window(req: Request):
    ip_addr = req.client.host
    if ip_addr in sliding_window_log:
        timestamp_list = sliding_window_log[ip_addr]
        # prune the old timestamps that are outside the now - N interval
        while timestamp_list and timestamp_list[0] < datetime.now() - timedelta(seconds=INTERVAL_SIZE_IN_SECONDS):
            timestamp_list.pop(0)
        if len(timestamp_list) + 1 <= THRESHOLD_PER_INTERVAL:
            timestamp_list.append(datetime.now())
            sliding_window_log[ip_addr] = timestamp_list
            return {"message": "Successful request"}
        else:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests received. Please try again later.",
                headers={"Retry-After": "60"}
            )
    else:
        sliding_window_log[ip_addr] = [datetime.now()]
        return {"message": "Request was successful!"}



                    
             







       
