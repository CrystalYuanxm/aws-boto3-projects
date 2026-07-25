# Bill Ingestion Pipeline — Amazon S3 + DynamoDB

A small Python tool that ingests a bill: it uploads the bill document to **Amazon S3**
and stores a matching metadata record in **Amazon DynamoDB**. Each database record links
back to its S3 object, so the file and its metadata always stay connected.

This follows the common **"object storage + metadata index"** pattern used in real data
pipelines: keep the large/raw object in S3, keep the queryable fields in a database, and
join them by a shared ID.

## Architecture

```
                  save_bill.py (boto3)
                          |
          put_object      |      put_item / get_item
        +-----------------+------------------+
        v                                    v
  +-----------+                       +--------------+
  | Amazon S3 |                       |   DynamoDB   |
  |  (bucket) |  <---- linked by ---> |   (table)    |
  |           |     s3Bucket / s3Key  |              |
  | bills/    |                       |  billId (PK) |
  |  <id>.json|                       |  + metadata  |
  +-----------+                       +--------------+
```

- The bill is stored in S3 as JSON at `bills/<billId>.json`.
- A DynamoDB item is written with the same `billId` plus `s3Bucket` and `s3Key`,
  so you can always find the object that belongs to a record.

## AWS services & tools

| Service / tool | Used for |
| --- | --- |
| Amazon S3 | Storing the raw bill document (`put_object`) |
| Amazon DynamoDB | Storing queryable metadata (`put_item`, `get_item`) |
| boto3 | AWS SDK for Python |
| uuid | Generating a unique `billId` for each bill |
| Decimal | Storing monetary values correctly in DynamoDB |

## How it works

1. Reads the target bucket and table names from **environment variables**
   (`S3_BUCKET`, `DYNAMODB_TABLE`) — no resource names are hard-coded.
2. Generates a unique `billId` with `uuid.uuid4()` and builds the S3 key
   `bills/<billId>.json`.
3. Uploads the bill as JSON to S3 with `ContentType="application/json"`.
4. Writes a matching DynamoDB item, storing the amount as `Decimal` (DynamoDB
   does not accept Python `float`) and including `s3Bucket` / `s3Key`.
5. Reads the item back with `get_item` and prints it to confirm the write.
6. Wraps all AWS calls in `try/except` and prints a clear error message on failure.

## Setup

### 1. Install dependencies

```bash
pip install boto3
```

### 2. Configure AWS credentials

Credentials live in `~/.aws/credentials` and the region in `~/.aws/config`
(on Windows: `%USERPROFILE%\.aws\`). Example:

```ini
# ~/.aws/credentials
[default]
aws_access_key_id = YOUR_KEY
aws_secret_access_key = YOUR_SECRET
aws_session_token = YOUR_TOKEN     # if your account uses temporary credentials
```

```ini
# ~/.aws/config
[default]
region = us-east-1
```

> Credentials are **never** committed to this repo (see `.gitignore`).

### 3. Create the AWS resources

- An S3 bucket (any name).
- A DynamoDB table with partition key **`billId` (String)**. Wait until its
  status is **Active**.

### 4. Set environment variables

```bash
export S3_BUCKET=your-bucket-name
export DYNAMODB_TABLE=your-table-name
```

(In PyCharm, add these under *Run → Edit Configurations → Environment variables*.)

## Run

```bash
python save_bill.py
```

### Sample output

```
Uploaded: bills/179f2bec-8a4a-4c35-b0bc-f36fa512c05f.json
Saved item
{'billId': '179f2bec-8a4a-4c35-b0bc-f36fa512c05f', 'accountNumber': Decimal('45231'),
 'billNumber': Decimal('187'), 'amountDue': Decimal('42.5'),
 's3Bucket': 'your-bucket-name', 's3Key': 'bills/179f2bec-....json'}
```

## What I learned

- Configuring AWS credentials locally and letting boto3 pick them up automatically.
- Using boto3's **client** API for S3 and the higher-level **resource/Table** API
  for DynamoDB.
- Why DynamoDB requires **`Decimal`** instead of `float` for numbers, and how that
  avoids floating-point precision issues with money.
- Designing around the **object-storage + metadata** pattern and linking the two
  stores with a shared key.
- Keeping configuration in **environment variables** instead of hard-coding it.
