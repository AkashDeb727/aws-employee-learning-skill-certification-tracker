import json
import boto3
from botocore.exceptions import ClientError
from decimal import Decimal

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("LSCT-Courses")

# Common CORS Headers
headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Content-Type": "application/json"
}


# Convert Decimal objects returned by DynamoDB to int/float
def decimal_default(obj):
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    raise TypeError


def lambda_handler(event, context):

    http_method = event.get("httpMethod")

    try:

        # ============================
        # GET /courses
        # ============================
        if http_method == "GET":

            response = table.scan()

            return {
                "statusCode": 200,
                "headers": headers,
                "body": json.dumps(
                    {
                        "courses": response.get("Items", [])
                    },
                    default=decimal_default
                )
            }

        # ============================
        # POST /courses
        # ============================
        elif http_method == "POST":

            body = json.loads(event["body"])

            course_id = body["course_id"]
            title = body["title"]
            description = body["description"]
            external_video_url = body["external_video_url"]
            passing_score = body["passing_score"]
            assigned_roles = body["assigned_roles"]

            # Check if course already exists
            response = table.get_item(
                Key={
                    "course_id": course_id
                }
            )

            if "Item" in response:
                return {
                    "statusCode": 409,
                    "headers": headers,
                    "body": json.dumps({
                        "message": "Course already exists"
                    })
                }

            table.put_item(
                Item={
                    "course_id": course_id,
                    "title": title,
                    "description": description,
                    "external_video_url": external_video_url,
                    "passing_score": passing_score,
                    "assigned_roles": assigned_roles
                }
            )

            return {
                "statusCode": 201,
                "headers": headers,
                "body": json.dumps({
                    "message": "Course created successfully",
                    "course_id": course_id
                })
            }

        # ============================
        # Unsupported Method
        # ============================
        else:
            return {
                "statusCode": 405,
                "headers": headers,
                "body": json.dumps({
                    "error": "Method Not Allowed"
                })
            }

    except KeyError as e:
        return {
            "statusCode": 400,
            "headers": headers,
            "body": json.dumps({
                "error": f"Missing field: {str(e)}"
            })
        }

    except ClientError as e:
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({
                "error": str(e)
            })
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({
                "error": str(e)
            })
        }