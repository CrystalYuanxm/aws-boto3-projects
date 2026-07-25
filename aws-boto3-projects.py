import os
import json
import boto3
import uuid
from decimal import Decimal

# S3 client for uploading the bill file
s3 = boto3.client("s3")

# Read the bucket name from an env var instead of hard-coding it
bucket_name = os.environ.get("S3_BUCKET")
if not bucket_name:
    raise ValueError("S3_BUCKET is not set")

# Unique id for this bill so files/records never collide
bill_id = str(uuid.uuid4())
key = f"bills/{bill_id}.json"  # e.g. bills/179f2bec-....json

# The bill data. Plain float here is fine because this dict is only
# turned into JSON for the S3 file (DynamoDB will use Decimal below)
bill = {
    "accountNumber": 45231,
    "billNumber": 187,
    "amountDue": 42.5,
}

try:
    # ---- 1. Upload the bill as a JSON file to S3 ----
    s3.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=json.dumps(bill),           # dict -> JSON string
        ContentType="application/json",  # so S3 knows it's JSON
    )
    print("Uploaded:", key)

    # ---- 2. Save a matching record in DynamoDB ----
    table_name = os.environ.get("DYNAMODB_TABLE")
    if not table_name:
        raise ValueError("DYNAMODB_TABLE is not set")

    table = boto3.resource("dynamodb").Table(table_name)

    table.put_item(
        Item={
            "billId": bill_id,               # partition key
            "accountNumber": 45231,
            "billNumber": 187,
            "amountDue": Decimal("42.5"),    # DynamoDB needs Decimal, not float
            "s3Bucket": bucket_name,         # where the file lives...
            "s3Key": key,                    # ...and its path, so we can find it later
        }
    )
    print("Saved item")

    # ---- 3. Read the record back to confirm it was written ----
    response = table.get_item(
        Key={"billId": bill_id}  # look it up by partition key
    )

    item = response.get("Item")
    if item is None:
        print("Not found")
    else:
        print(item)

# Catch any AWS/network error and show a readable message
except Exception as e:
    print("Error:", e)