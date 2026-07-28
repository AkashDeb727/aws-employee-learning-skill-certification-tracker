import json
import boto3
import hashlib
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")

courses_table = dynamodb.Table("LSCT-Courses")
quizzes_table = dynamodb.Table("LSCT-Quizzes")

headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Methods": "POST,OPTIONS"
}


def lambda_handler(event, context):
    try:
        body = json.loads(event["body"])

        path_params = event.get("pathParameters") or {}
        course_id = path_params.get("course_id")
        questions = body.get("questions")

        if not course_id:
            return response(400, {"message": "course_id is required"})

        if not questions or not isinstance(questions, list):
            return response(400, {"message": "questions must be a non-empty array"})

        # Check course exists
        course = courses_table.get_item(
            Key={
                "course_id": course_id
            }
        )

        if "Item" not in course:
            return response(404, {"message": "Course not found"})

        # Existing questions
        existing = quizzes_table.query(
            KeyConditionExpression=Key("course_id").eq(course_id)
        )

        next_number = len(existing.get("Items", [])) + 1

        added_questions = []

        for q in questions:

            question = q.get("question")
            options = q.get("options")
            correct_answer = q.get("correct_answer")
            marks = q.get("marks", 1)

            if not all([question, options, correct_answer]):
                return response(
                    400,
                    {
                        "message": "Each question must contain question, options and correct_answer"
                    }
                )

            question_id = f"Q{next_number}"
            next_number += 1

            correct_answer_hash = hashlib.sha256(
                correct_answer.encode("utf-8")
            ).hexdigest()

            quizzes_table.put_item(
                Item={
                    "course_id": course_id,
                    "question_id": question_id,
                    "question": question,
                    "options": options,
                    "correct_answer_hash": correct_answer_hash,
                    "marks": marks
                }
            )

            added_questions.append(question_id)

        return response(
            201,
            {
                "message": "Quiz questions added successfully",
                "questions_added": len(added_questions),
                "question_ids": added_questions
            }
        )

    except ClientError as e:
        return response(500, {"message": str(e)})

    except Exception as e:
        return response(500, {"message": str(e)})


def response(status, body):
    return {
        "statusCode": status,
        "headers": headers,
        "body": json.dumps(body)
    }