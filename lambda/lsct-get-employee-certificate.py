import json
import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")

# DynamoDB Table
certificates_table = dynamodb.Table("LSCT-Certificates")

# CORS Headers
headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
    "Content-Type": "application/json"
}


def lambda_handler(event, context):
    try:
        # Get Employee ID
        employee_id = (
            event.get("pathParameters", {})
                 .get("employee_id")
        )

        if not employee_id:
            return {
                "statusCode": 400,
                "headers": headers,
                "body": json.dumps({
                    "message": "Employee ID is required."
                })
            }

        # Scan the table
        response = certificates_table.scan()

        items = response.get("Items", [])

        # Find certificate for this employee
        certificate = next(
            (item for item in items if item.get("employee_id") == employee_id),
            None
        )

        if not certificate:
            return {
                "statusCode": 404,
                "headers": headers,
                "body": json.dumps({
                    "message": "No certificate found for this employee."
                })
            }

        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({
                "certificate_id": certificate.get("certificate_id"),
                "employee_id": certificate.get("employee_id"),
                "employee_name": certificate.get("employee_name"),
                "course_id": certificate.get("course_id"),
                "course_title": certificate.get("course_title"),
                "completion_date": certificate.get("completion_date"),
                "s3_path": certificate.get("s3_path")
            })
        }

    except ClientError as e:
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({
                "message": "Database Error",
                "error": str(e)
            })
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({
                "message": "Internal Server Error",
                "error": str(e)
            })
        }