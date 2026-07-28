import json
import boto3
from boto3.dynamodb.conditions import Key

# DynamoDB Resource
dynamodb = boto3.resource("dynamodb")
quiz_table = dynamodb.Table("LSCT-Quizzes")

# Common Response Headers
HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "GET,OPTIONS"
}


def lambda_handler(event, context):
    try:
        course_id = event["pathParameters"]["course_id"]

        response = quiz_table.query(
            KeyConditionExpression=Key("course_id").eq(course_id)
        )

        items = response.get("Items", [])

        if not items:
            return {
                "statusCode": 404,
                "headers": HEADERS,
                "body": json.dumps({
                    "error": "Quiz not found"
                })
            }

        questions = []

        for item in items:
            questions.append({
                "question_id": item["question_id"],
                "question": item["question"],
                "options": item["options"]
            })

        return {
            "statusCode": 200,
            "headers": HEADERS,
            "body": json.dumps({
                "course_id": course_id,
                "total_questions": len(questions),
                "questions": questions
            })
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": HEADERS,
            "body": json.dumps({
                "error": str(e)
            })
        }