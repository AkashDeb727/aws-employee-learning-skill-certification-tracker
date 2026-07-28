import json
import boto3

dynamodb = boto3.resource("dynamodb")

employees_table = dynamodb.Table("LSCT-Employees")
assignments_table = dynamodb.Table("LSCT-Assignments")
completions_table = dynamodb.Table("LSCT-Completions")

# Common CORS Headers
headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
    "Content-Type": "application/json"
}


def lambda_handler(event, context):

    try:

        path = event.get("resource", "")

        employees = employees_table.scan().get("Items", [])
        assignments = assignments_table.scan().get("Items", [])
        completions = completions_table.scan().get("Items", [])

        # =====================================
        # GET /dashboard/employee-status
        # =====================================
        if path == "/dashboard/employee-status":

            employee_status = []

            for assignment in assignments:

                employee_id = assignment["employee_id"]
                course_id = assignment["course_id"]

                status = "not_started"

                for completion in completions:

                    if (
                        completion["employee_id"] == employee_id
                        and completion["course_id"] == course_id
                    ):

                        result = completion.get("result", "").upper()

                        if result == "PASS":
                            status = "passed"
                        elif result == "FAIL":
                            status = "failed"
                        else:
                            status = "in_progress"

                        break

                employee_status.append({
                    "employee_id": employee_id,
                    "course_id": course_id,
                    "status": status
                })

            return {
                "statusCode": 200,
                "headers": headers,
                "body": json.dumps({
                    "employees": employee_status
                })
            }

        # =====================================
        # GET /dashboard/skill-matrix
        # =====================================
        elif path == "/dashboard/skill-matrix":

            department_stats = {}

            for employee in employees:

                department = employee["department"]

                if department not in department_stats:
                    department_stats[department] = {
                        "total": 0,
                        "completed": 0
                    }

                department_stats[department]["total"] += 1

                employee_completed = False

                for completion in completions:

                    if (
                        completion["employee_id"] == employee["employee_id"]
                        and completion.get("result", "").upper() == "PASS"
                    ):
                        employee_completed = True
                        break

                if employee_completed:
                    department_stats[department]["completed"] += 1

            departments = []

            for dept, values in department_stats.items():

                percent = 0

                if values["total"] > 0:
                    percent = round(
                        (values["completed"] / values["total"]) * 100,
                        2
                    )

                departments.append({
                    "department": dept,
                    "mandatory_courses_completed_percent": percent
                })

            return {
                "statusCode": 200,
                "headers": headers,
                "body": json.dumps({
                    "departments": departments
                })
            }

        # =====================================
        # Invalid endpoint
        # =====================================
        else:
            return {
                "statusCode": 404,
                "headers": headers,
                "body": json.dumps({
                    "error": "Endpoint not found"
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