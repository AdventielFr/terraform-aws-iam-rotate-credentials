resource "aws_sns_topic" "iam_rotate_credentials_result" {
  name         = "${local.service_name}-result"
  display_name = "Topic for IAM rotate credentials result"
  tags         = local.tags
}

resource "aws_sqs_queue" "update_iam_credentials_for_user" {
  name                       = local.sqs_name
  visibility_timeout_seconds = 300
  max_message_size           = 2048
  message_retention_seconds  = 86400
  policy                     = data.aws_iam_policy_document.sqs_policy.json
  redrive_policy             = "{\"deadLetterTargetArn\":\"${aws_sqs_queue.update_iam_credentials_for_user_dead_letter.arn}\",\"maxReceiveCount\":1}"
  tags                       = local.tags
  depends_on = [
    aws_sqs_queue.update_iam_credentials_for_user_dead_letter
  ]
}

resource "aws_sqs_queue" "update_iam_credentials_for_user_dead_letter" {
  name = "${local.sqs_name}-dead-letter"
  tags = local.tags
}

