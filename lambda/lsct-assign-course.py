import json
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
ses = boto3.client('ses')

courses_table = dynamodb.Table('LSCT-Courses')
employees_table = dynamodb.Table('LSCT-Employees')
assignments_table = dynamodb.Table('LSCT-Assignments')

# CORS Headers
headers = {
    "Access-Control-Allow-Origin": "*",
    "Content-Type": "application/json"
}


def lambda_handler(event, context):

    try:
        body = json.loads(event["body"])

        path_params = event.get("pathParameters") or {}
        course_id = path_params.get("course_id")

        employee_ids = body.get("employee_ids", [])
        assigned_roles = body.get("assigned_roles", [])
        due_date = body.get("due_date")

        if not course_id:
            return {
                "statusCode": 400,
                "headers": headers,
                "body": json.dumps({
                    "error": "course_id is required"
                })
            }

        # Check if course exists
        response = courses_table.get_item(
            Key={
                "course_id": course_id
            }
        )

        if "Item" not in response:
            return {
                "statusCode": 404,
                "headers": headers,
                "body": json.dumps({
                    "error": "Course not found"
                })
            }

        assigned = []

        for emp in employee_ids:

            employee = employees_table.get_item(
                Key={
                    "employee_id": emp
                }
            )

            if "Item" in employee:

                employee_email = employee["Item"]["email"]
                employee_name = employee["Item"]["name"]

                assignments_table.put_item(
                    Item={
                        "employee_id": emp,
                        "course_id": course_id,
                        "assigned_date": datetime.now().strftime("%Y-%m-%d"),
                        "due_date": due_date,
                        "status": "Assigned"
                    }
                )

                ses.send_email(
                    Source="ibrahimajmeri07@gmail.com",
                    Destination={
                        "ToAddresses": [
                            employee_email
                        ]
                    },
                    Message={
                        "Subject": {
                            "Data": "New Course Assigned"
                        },
                        "Body": {
                            "Text": {
                                "Data": f"""Hello {employee_name},

A new course has been assigned to you.

Course ID: {course_id}
Due Date: {due_date}

Please complete the course before the due date.

Regards,
LSCT Team
"""
                            }
                        }
                    }
                )

                assigned.append(emp)

        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({
                "message": "Course assigned successfully",
                "course_id": course_id,
                "assigned_employees": assigned
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