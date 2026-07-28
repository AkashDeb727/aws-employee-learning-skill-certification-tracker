import json
import boto3
import uuid
import os
from decimal import Decimal
from datetime import datetime

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor

# AWS Clients
s3 = boto3.client("s3")
ses = boto3.client("ses")
dynamodb = boto3.resource("dynamodb")

# DynamoDB Tables
employees_table = dynamodb.Table("LSCT-Employees")
courses_table = dynamodb.Table("LSCT-Courses")
completions_table = dynamodb.Table("LSCT-Completions")
certificates_table = dynamodb.Table("LSCT-Certificates")

# Environment Variables
BUCKET_NAME = os.getenv("CERTIFICATE_BUCKET")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")

headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
    "Content-Type": "application/json"
}

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError


def lambda_handler(event, context):

    try:

        employee_id = event["employee_id"]
        course_id = event["course_id"]


        # ==========================
        # Get Employee
        # ==========================
        employee = employees_table.get_item(
            Key={
                "employee_id": employee_id
            }
        )

        if "Item" not in employee:
            return {
                "statusCode": 404,
                "headers": headers,
                "body": json.dumps({
                    "message": "Employee not found"
                })
            }

        # ==========================
        # Get Course
        # ==========================
        course = courses_table.get_item(
            Key={
                "course_id": course_id
            }
        )

        if "Item" not in course:
            return {
                "statusCode": 404,
                "headers": headers,
                "body": json.dumps({
                    "message": "Course not found"
                })
            }

        employee_data = employee["Item"]
        course_data = course["Item"]

        employee_name = employee_data["name"]
        course_name = course_data["title"]
        employee_email = employee_data["email"]

        # ==========================
        # Check Quiz Result
        # ==========================

        completion = completions_table.get_item(
            Key={
                "employee_id": employee_id,
                "course_id": course_id
            }
        )

        if "Item" not in completion:
            return {
                "statusCode": 404,
                "headers": headers,
                "body": json.dumps({
                    "message": "Quiz completion not found."
                })
            }

        if completion["Item"]["result"] != "PASS":
            return {
                "statusCode": 400,
                "headers": headers,
                "body": json.dumps({
                    "message": "Certificate can only be generated for passed quizzes."
                })
            }

        # ==========================
        # Generate Certificate ID
        # ==========================
        certificate_id = "CERT-" + uuid.uuid4().hex[:8].upper()

        completion_date = datetime.utcnow().strftime("%d %B %Y")

        # ==========================
        # Generate PDF
        # ==========================
        pdf_path = "/tmp/certificate.pdf"

        c = canvas.Canvas(pdf_path, pagesize=letter)

        width, height = letter

        primary_color = HexColor("#163A5F")

        # =====================================================
        # Borders
        # =====================================================

        c.setStrokeColor(primary_color)
        c.setLineWidth(3)
        c.rect(30, 30, width - 60, height - 60)

        c.setLineWidth(1)
        c.rect(55, 55, width - 110, height - 110)

        # =====================================================
        # Title
        # =====================================================

        c.setFillColor(primary_color)
        c.setFont("Helvetica-Bold", 30)
        c.drawCentredString(width / 2, 705, "CERTIFICATE OF COMPLETION")

        c.setLineWidth(2)
        c.line(145, 685, width - 145, 685)

        # =====================================================
        # Presented To
        # =====================================================

        c.setFillColor(HexColor("#000000"))

        c.setFont("Helvetica", 15)
        c.drawCentredString(
            width / 2,
            625,
            "This certificate is proudly presented to"
        )

        # =====================================================
        # Employee Name
        # =====================================================

        c.setFillColor(primary_color)

        c.setFont("Helvetica-Bold", 30)
        c.drawCentredString(
            width / 2,
            575,
            employee_name
        )

        # =====================================================
        # Completion Text
        # =====================================================

        c.setFillColor(HexColor("#000000"))

        c.setFont("Helvetica", 15)
        c.drawCentredString(
            width / 2,
            525,
            "For successfully completing the course"
        )

        # =====================================================
        # Course Name
        # =====================================================

        c.setFillColor(primary_color)

        c.setFont("Helvetica-Bold", 24)
        c.drawCentredString(
            width / 2,
            480,
            course_name
        )

        # =====================================================
        # Footer
        # =====================================================

        c.setFillColor(HexColor("#000000"))

        c.setFont("Helvetica-Bold", 13)
        c.drawCentredString(width / 2, 205, "Completion Date")

        c.setFont("Helvetica", 13)
        c.drawCentredString(width / 2, 185, completion_date)

        c.setFont("Helvetica-Bold", 13)
        c.drawCentredString(width / 2, 145, "Certificate ID")

        c.setFont("Helvetica", 13)
        c.drawCentredString(width / 2, 125, certificate_id)

        c.save()

        # ==========================
        # Upload to S3
        # ==========================
        s3_key = f"certificates/{employee_id}/{course_id}.pdf"

        s3.upload_file(
            pdf_path,
            BUCKET_NAME,
            s3_key
        )

        certificate_url = s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": BUCKET_NAME,
                "Key": s3_key
            },
            ExpiresIn=604800  # 7 days
        )

        # ==========================
        # Store Certificate Metadata
        # ==========================

        certificates_table.put_item(
            Item={
                "certificate_id": certificate_id,
                "employee_id": employee_id,
                "employee_name": employee_name,
                "course_id": course_id,
                "course_title": course_name,
                "completion_date": completion_date,
                "s3_path": s3_key
            }
        )

        ses.send_templated_email(
            Source=SENDER_EMAIL,
            Destination={
                "ToAddresses": [employee_email]
            },
            Template="certificate_completion_email",
            TemplateData=json.dumps({
                "employee_name": employee_name,
                "course_name": course_name,
                "certificate_id": certificate_id,
                "completion_date": completion_date,
                "certificate_url": certificate_url
            })
        )

        # ==========================
        # Success Response
        # ==========================
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps(
                {
                    "message": "Certificate generated successfully",
                    "certificate_id": certificate_id,
                    "employee": employee_name,
                    "course": course_name,
                    "completion_date": completion_date,
                    "s3_key": s3_key
                },
                default=decimal_default
            )
        }

    except Exception as err:

        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({
                "error": str(err)
            })
        }