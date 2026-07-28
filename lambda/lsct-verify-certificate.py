import json
import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")

# Table
certificates_table = dynamodb.Table("LSCT-Certificates")

# Common CORS Headers
headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
    "Content-Type": "application/json"
}


def lambda_handler(event, context):
    try:
        # Get certificate ID from path parameter
        path_params = event.get("pathParameters") or {}
        certificate_id = path_params.get("cert_id")

        if not certificate_id:
            return {
                "statusCode": 400,
                "headers": headers,
                "body": json.dumps({
                    "message": "Certificate ID is required."
                })
            }

        # Retrieve certificate from DynamoDB
        response = certificates_table.get_item(
            Key={
                "certificate_id": certificate_id
            }
        )

        # Certificate not found
        if "Item" not in response:
            return {
                "statusCode": 404,
                "headers": headers,
                "body": json.dumps({
                    "certificate_id": certificate_id,
                    "valid": False,
                    "error": "Certificate not found"
                })
            }

        certificate = response["Item"]

        # Certificate found
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({
                "certificate_id": certificate["certificate_id"],
                "employee_id": certificate["employee_id"],
                "employee_name": certificate["employee_name"],
                "course_id": certificate["course_id"],
                "course_title": certificate["course_title"],
                "completion_date": certificate["completion_date"],
                "valid": True
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