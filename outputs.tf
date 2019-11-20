
output "lambda_arn" {
  description = "The Lambda ARN of IAM rotate Credentials"
  value       = aws_lambda_function.iam_rotate_credentials.arn
}

output "sns_result_arn" {
  description = "The SNS result ARN of topic for result IAM rotate Credential lambda execution"
  value       = aws_sns_topic.iam_rotate_credentials_result.arn
}