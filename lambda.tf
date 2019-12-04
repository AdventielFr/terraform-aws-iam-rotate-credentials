resource "aws_lambda_function" "find_users_to_refresh" {
  function_name = local.lambda_find_users_to_refresh_name
  memory_size   = 128
  description   = "Research the users for which it is necessary to refresh their credentials"
  timeout       = var.function_timeout
  runtime       = "python3.7"
  filename      = "${path.module}/iam-rotate-credentials.zip"
  handler       = "lambdaFindUsersToRefreshHandler.main"
  role          = aws_iam_role.find_users_to_refresh.arn
  kms_key_arn   = aws_kms_key.iam_rotate_credentials.arn

  environment {
    variables = {
      AWS_SNS_RESULT_ARN           = aws_sns_topic.iam_rotate_credentials_result.arn
      AWS_CLI_TIME_LIMIT           = var.aws_cli_time_limit
      AWS_LOGIN_PROFILE_TIME_LIMIT = var.aws_login_profile_time_limit
      AWS_SQS_REQUEST_URL          = local.sqs_url
    }
  }

  tags = merge(local.tags, map("Lambda", local.lambda_find_users_to_refresh_name))

  depends_on = [
    aws_iam_role_policy_attachment.find_users_to_refresh,
    aws_cloudwatch_log_group.find_users_to_refresh
  ]
}

resource "aws_lambda_function" "update_iam_credentials_for_user" {
  function_name = local.lambda_update_iam_credentials_for_user_name
  memory_size   = 128
  description   = "Update the credentials for the user contained in message from SQS"
  timeout       = var.function_timeout
  runtime       = "python3.7"
  filename      = "${path.module}/iam-rotate-credentials.zip"
  handler       = "lambdaUpdateIamCredentialsForUserHandler.main"
  role          = aws_iam_role.update_iam_credentials_for_user.arn
  kms_key_arn   = aws_kms_key.iam_rotate_credentials.arn

  environment {
    variables = {
      AWS_CLI_TIME_LIMIT                        = var.aws_cli_time_limit
      AWS_LOGIN_PROFILE_TIME_LIMIT              = var.aws_login_profile_time_limit
      AWS_LOGIN_PROFILE_PASSWORD_RESET_REQUIRED = var.aws_login_profile_password_reset_required
      AWS_SES_EMAIL_FROM                        = var.aws_ses_email_from
      AWS_SNS_RESULT_ARN                        = aws_sns_topic.iam_rotate_credentials_result.arn
      CREDENTIALS_SENDED_BY                     = var.credentials_sended_by
    }
  }

  tags = merge(local.tags, map("Lambda", local.lambda_update_iam_credentials_for_user_name))

  depends_on = [
    aws_iam_role_policy_attachment.update_iam_credentials_for_user,
    aws_cloudwatch_log_group.update_iam_credentials_for_user
  ]
}

resource "aws_lambda_permission" "allow_cloudwatch_to_call_lambda" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.find_users_to_refresh.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.every_x_minutes.arn
}

resource "aws_lambda_event_source_mapping" "iam_rotate_credentials_request" {
  event_source_arn = aws_sqs_queue.update_iam_credentials_for_user.arn
  function_name    = aws_lambda_function.update_iam_credentials_for_user.arn
  enabled          = true
  depends_on = [
    aws_sqs_queue.update_iam_credentials_for_user,
    aws_lambda_function.update_iam_credentials_for_user
  ]
}
