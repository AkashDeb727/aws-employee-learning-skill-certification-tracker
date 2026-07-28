import json
import boto3
import hashlib
from decimal import Decimal
from datetime import datetime, timezone
from boto3.dynamodb.conditions import Key

lambda_client = boto3.client("lambda")
dynamodb = boto3.resource("dynamodb")

employees_table = dynamodb.Table("LSCT-Employees")
courses_table = dynamodb.Table("LSCT-Courses")
quizzes_table = dynamodb.Table("LSCT-Quizzes")
completions_table = dynamodb.Table("LSCT-Completions")

# Common CORS Headers
headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
    "Content-Type": "application/json"
}


def sha256_hash(answer):
    return hashlib.sha256(answer.strip().upper().encode()).hexdigest()


def lambda_handler(event, context):
    try:
        # -----------------------------
        # Read Request
        # -----------------------------
        course_id = event["pathParameters"]["course_id"]

        body = json.loads(event["body"])

        employee_id = body.get("employee_id")
        answers = body.get("answers")

        # -----------------------------
        # Input Validation
        # -----------------------------
        if not employee_id:
            return response(400, "employee_id is required")

        if not course_id:
            return response(400, "course_id is required")

        if answers is None:
            return response(400, "answers field is required")

        if len(answers) == 0:
            return response(400, "answers cannot be empty")

        # -----------------------------
        # Validate Employee
        # -----------------------------
        employee = employees_table.get_item(
            Key={
                "employee_id": employee_id
            }
        )

        if "Item" not in employee:
            return response(404, "Employee not found")

        # -----------------------------
        # Validate Course
        # -----------------------------
        course = courses_table.get_item(
            Key={
                "course_id": course_id
            }
        )

        if "Item" not in course:
            return response(404, "Course not found")

        # -----------------------------
        # Read Course Details
        # -----------------------------
        course_item = course["Item"]
        passing_score = course_item["passing_score"]

        # -----------------------------
        # Retrieve Quiz Questions
        # -----------------------------
        quiz_response = quizzes_table.query(
            KeyConditionExpression=Key("course_id").eq(course_id)
        )

        quiz_questions = quiz_response["Items"]

        if not quiz_questions:
            return response(404, "No quiz found for this course")

        # -----------------------------
        # Create Lookup Dictionary
        # -----------------------------
        quiz_lookup = {}

        for question in quiz_questions:
            quiz_lookup[question["question_id"]] = question

        # -----------------------------
        # Grade Quiz
        # -----------------------------
        score = 0
        total_marks = 0

        correct_answers = 0
        total_questions = len(quiz_questions)

        for answer in answers:

            question_id = answer.get("question_id")
            selected_option = answer.get("selected_option")

            if not question_id or not selected_option:
                continue

            if question_id not in quiz_lookup:
                continue

            question = quiz_lookup[question_id]

            total_marks += question["marks"]

            selected_option_hash = sha256_hash(selected_option)

            if selected_option_hash == question["correct_answer_hash"]:
                score += question["marks"]
                correct_answers += 1

        # -----------------------------
        # Determine Result
        # -----------------------------
        if score >= passing_score:
            result = "PASS"
        else:
            result = "FAIL"

        completed_at = datetime.now(timezone.utc).isoformat()

        # -----------------------------
        # Check Previous Completion
        # -----------------------------
        existing_completion = completions_table.get_item(
            Key={
                "employee_id": employee_id,
                "course_id": course_id
            }
        )

        MAX_ATTEMPTS = 3

        if "Item" in existing_completion:

            previous_attempts = existing_completion["Item"].get("attempt_count", 0)

            if previous_attempts >= MAX_ATTEMPTS:
                return response(
                    403,
                    f"Maximum quiz attempts ({MAX_ATTEMPTS}) exceeded."
                )

            attempt_count = previous_attempts + 1

        else:
            attempt_count = 1

        # -----------------------------
        # Save Quiz Completion
        # -----------------------------
        completions_table.put_item(
            Item={
                "employee_id": employee_id,
                "course_id": course_id,
                "attempt_count": attempt_count,
                "score": score,
                "total_marks": total_marks,
                "passing_score": passing_score,
                "correct_answers": correct_answers,
                "total_questions": total_questions,
                "result": result,
                "completed_at": completed_at
            }
        )

        # -----------------------------
        # Generate Certificate
        # -----------------------------
        if result == "PASS":
            lambda_client.invoke(
                FunctionName="lsct-generate-certificate",
                InvocationType="RequestResponse",
                Payload=json.dumps({
                    "employee_id": employee_id,
                    "course_id": course_id
                })
            )

        # -----------------------------
        # Success Response
        # -----------------------------
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps(
                {
                    "message": "Quiz evaluated successfully",
                    "employee_id": employee_id,
                    "course_id": course_id,
                    "attempt_count": attempt_count,
                    "score": score,
                    "total_marks": total_marks,
                    "passing_score": passing_score,
                    "correct_answers": correct_answers,
                    "total_questions": total_questions,
                    "result": result,
                    "completed_at": completed_at
                },
                default=decimal_default
            )
        }

    except Exception as e:
        return response(500, str(e))


def decimal_default(obj):
    """
    Converts DynamoDB Decimal values into JSON-serializable numbers.
    """
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def response(status_code, message):
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps({
            "error": message
        })
    }