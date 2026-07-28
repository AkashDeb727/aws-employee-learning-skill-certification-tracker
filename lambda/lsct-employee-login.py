import json
import boto3
from botocore.exceptions import ClientError
# CI/CD pipeline validation
# DynamoDB
dynamodb = boto3.resource("dynamodb")
employees_table = dynamodb.Table("LSCT-Employees")

# CORS Headers
headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Methods": "POST,OPTIONS"
}


def lambda_handler(event, context):

    # Handle CORS Preflight
    if event.get("httpMethod") == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({})
        }

    try:
        body = json.loads(event.get("body", "{}"))

        employee_id = body.get("employee_id")

        if not employee_id:
            return {
                "statusCode": 400,
                "headers": headers,
                "body": json.dumps({
                    "success": False,
                    "message": "Employee ID is required"
                })
            }

        response = employees_table.get_item(
            Key={
                "employee_id": employee_id
            }
        )

        if "Item" not in response:
            return {
                "statusCode": 404,
                "headers": headers,
                "body": json.dumps({
                    "success": False,
                    "message": "Invalid Employee ID"
                })
            }

        employee = response["Item"]

        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({
                "success": True,
                "message": "Login successful",
                "employee": employee
            })
        }

    except ClientError as e:
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({
                "success": False,
                "message": e.response["Error"]["Message"]
            })
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({
                "success": False,
                "message": str(e)
            })
        }
