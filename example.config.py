import os

port= int(os.environ.get("PORT")) if os.environ.get("PORT") else 8080
api_url= os.environ.get("API_URL") if os.environ.get("API_URL") else "https://api2.nicehash.com"
api_url_prefix= os.environ.get("API_URL_PREFIX") if os.environ.get("API_URL_PREFIX") else "/main/api/v2"
organization_id= os.environ.get("ORGANIZATION_ID") if os.environ.get("ORGANIZATION_ID") else ""
key= os.environ.get("KEY") if os.environ.get("KEY") else ""
key_secret= os.environ.get("KEY_SECRET") if os.environ.get("KEY_SECRET") else ""