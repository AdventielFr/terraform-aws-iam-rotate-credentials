
resource "aws_cloudwatch_log_group" "find_users_to_refresh" {
  name              = "/aws/lambda/${local.lambda_find_users_to_refresh_name}"
  retention_in_days = var.cloudwatch_log_retention
}

resource "aws_cloudwatch_log_group" "update_iam_credentials_for_user" {
  name              = "/aws/lambda/${local.lambda_update_iam_credentials_for_user_name}"
  retention_in_days = var.cloudwatch_log_retention
}

resource "aws_cloudwatch_event_rule" "every_x_minutes" {
  name                = "${local.lambda_find_users_to_refresh_name}-schedule"
  description         = "Research the uses for which it is necessary to refresh their credentials Fires every ${var.scan_alarm_clock} minutes"
  schedule_expression = "rate(${var.scan_alarm_clock} minutes)"
}

resource "aws_cloudwatch_event_target" "check_every_x_minutes" {
  rule      = aws_cloudwatch_event_rule.every_x_minutes.name
  target_id = local.lambda_find_users_to_refresh_name
  arn       = aws_lambda_function.find_users_to_refresh.arn
}