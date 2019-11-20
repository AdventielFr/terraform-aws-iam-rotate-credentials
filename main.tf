data "aws_caller_identity" "current" {}

locals {
  lambda_name = "iam-rotate-credentials"
}

data "aws_iam_policy_document" "iam_rotate_credentials" {

  statement {
    sid       = "AllowSESAccess"
    effect    = "Allow"
    resources = ["*"]

    actions = [
      "ses:ListIdentities",
      "ses:SendEmail",
      "ses:SendRawEmail",
      "ses:SendTemplatedEmail",
      "ses:GetIdentityVerificationAttributes"
    ]
  }

  statement {
    sid       = "AllowIAMAccess"
    effect    = "Allow"
    resources = ["*"]

    actions = [
      "iam:CreateAccessKey",
      "iam:DeleteAccessKey",
      "iam:GetLoginProfile",
      "iam:GetUser",
      "iam:ListAccessKeys",
      "iam:ListUsers",
      "iam:UpdateLoginProfile",
      "iam:ListUserTags"
    ]
  }

  statement {
    sid       = "AllowSNSPermissions"
    effect    = "Allow"
    resources = [aws_sns_topic.iam_rotate_credentials_result.arn]

    actions = [
      "sns:Publish"
    ]
  }

  statement {
    sid    = "AllowCloudwatchAccess"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = [
      "*",
    ]
  }

}

resource "aws_iam_policy" "iam_rotate_credentials" {
  name   = "${local.lambda_name}-policy"
  policy = data.aws_iam_policy_document.iam_rotate_credentials.json
}

resource "aws_iam_role" "iam_rotate_credentials" {
  name               = "${local.lambda_name}-role"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
  tags = {
    Lambda = local.lambda_name
  }
}

resource "aws_iam_role_policy_attachment" "iam_rotate_credentials" {
  policy_arn = aws_iam_policy.iam_rotate_credentials.arn
  role       = aws_iam_role.iam_rotate_credentials.name
}

resource "aws_cloudwatch_log_group" "iam_rotate_credentials" {
  name              = "/aws/lambda/${local.lambda_name}"
  retention_in_days = var.cloudwatch_log_retention
}

resource "aws_lambda_function" "iam_rotate_credentials" {
  function_name = local.lambda_name
  memory_size   = 128
  description   = "Feature allowing the current list of iam credentials as they become obsolete"
  timeout       = var.function_timeout
  runtime       = "python3.6"
  filename      = "${path.module}/iam-rotate-credentials.zip"
  handler       = "handler.main"
  role          = aws_iam_role.iam_rotate_credentials.arn

  environment {
    variables = {
      AWS_CLI_TIME_LIMIT                        = var.aws_cli_time_limit
      AWS_LOGIN_PROFILE_TIME_LIMIT              = var.aws_login_profile_time_limit
      AWS_LOGIN_PROFILE_PASSWORD_RESET_REQUIRED = var.aws_login_profile_password_reset_required
      AWS_SES_EMAIL_FROM                        = var.aws_ses_email_from
      AWS_SNS_RESULT_ARN                        = aws_sns_topic.iam_rotate_credentials_result.arn
    }
  }

  tags = {
    Lambda = local.lambda_name
  }

  depends_on = [
    aws_iam_role_policy_attachment.iam_rotate_credentials,
    aws_cloudwatch_log_group.iam_rotate_credentials
  ]
}

resource "aws_cloudwatch_event_rule" "every_x_minutes" {
  name                = "${local.lambda_name}-schedule"
  description         = "${local.lambda_name} Fires every ${var.scan_alarm_clock} minutes"
  schedule_expression = "rate(${var.scan_alarm_clock} minutes)"
}

resource "aws_cloudwatch_event_target" "check_every_x_minutes" {
  rule      = aws_cloudwatch_event_rule.every_x_minutes.name
  target_id = local.lambda_name
  arn       = aws_lambda_function.iam_rotate_credentials.arn
}

resource "aws_lambda_permission" "allow_cloudwatch_to_call_lambda" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.iam_rotate_credentials.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.every_x_minutes.arn
}

resource "aws_sns_topic" "iam_rotate_credentials_result" {
  name         = "${local.lambda_name}-result"
  display_name = "Topic for ${local.lambda_name} result"
  tags = {
    Lambda = local.lambda_name
  }
}