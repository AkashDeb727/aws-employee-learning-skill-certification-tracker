import json
import boto3
from decimal import Decimal
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")

assignments_table = dynamodb.Table("LSCT-Assignments")
courses_table = dynamodb.Table("LSCT-Courses")

# CORS Headers
headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
    "Content-Type": "application/json"
}


def convert_decimals(obj):
    """
    Recursively convert DynamoDB Decimal objects
    into normal Python int/float values.
    """
    if isinstance(obj, list):
        return [convert_decimals(i) for i in obj]

    elif isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}

    elif isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)

    return obj


def lambda_handler(event, context):
    try:
        # Get employee ID
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

        # Get employee assignments
        assignment_response = assignments_table.query(
            KeyConditionExpression=Key("employee_id").eq(employee_id)
        )

        assignments = assignment_response.get("Items", [])

        if not assignments:
            return {
                "statusCode": 200,
                "headers": headers,
                "body": json.dumps([])
            }

        courses = []

        for assignment in assignments:

            course_response = courses_table.get_item(
                Key={
                    "course_id": assignment["course_id"]
                }
            )

            if "Item" not in course_response:
                continue

            course = course_response["Item"]

            courses.append({
                "course_id": course.get("course_id"),
                "title": course.get("title"),
                "description": course.get("description"),
                "passing_score": course.get("passing_score"),
                "external_video_url": course.get("external_video_url"),
                "assigned_roles": course.get("assigned_roles"),
                "assigned_date": assignment.get("assigned_date"),
                "due_date": assignment.get("due_date"),
                "status": assignment.get("status")
            })

        # Convert every Decimal recursively
        courses = convert_decimals(courses)

        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps(courses)
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