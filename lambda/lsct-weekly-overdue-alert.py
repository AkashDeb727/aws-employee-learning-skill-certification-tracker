import json
import boto3
from datetime import datetime, timedelta

dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")

TABLE_NAME = "LSCT-Assignments"
TOPIC_ARN = "arn:aws:sns:ap-south-1:443496863626:seo-hr-alerts-topic"

table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    response = table.scan()
    items = response.get("Items", [])

    today = datetime.utcnow().date()
    overdue = []

    for item in items:
        due_date = item.get("due_date")
        status = item.get("status", "").lower()

        if due_date and status != "completed":
            due = datetime.strptime(due_date, "%Y-%m-%d").date()

            if due < today:
                overdue.append(
                    f"{item['employee_id']} - {item['course_id']} (Due: {due_date})"
                )

    if overdue:
        message = "Weekly Overdue Assignments:\n\n" + "\n".join(overdue)

        sns.publish(
            TopicArn=TOPIC_ARN,
            Subject="Weekly Overdue Assignment Alert",
            Message=message
        )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "overdue_count": len(overdue),
            "overdue": overdue
        })
    }