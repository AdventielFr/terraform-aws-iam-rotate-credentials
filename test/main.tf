
provider "aws" {
  region = "eu-west-1"
}

module "iam_rotate_credentials" {
  source                       = "../"
  aws_region                   = "eu-west-1"
  aws_ses_email_from           = "no-reply@adventiel.fr"
  aws_login_profile_time_limit = 10
  aws_cli_time_limit           = 15
  tags = {
    Department = "ops"
    Owner = "adventiel"
  }
}

output "lambda_update_iam_credentials_for_user_arn" {
  description = "The Lambda ARN of Update IAM credentials lambda"
  value       = module.iam_rotate_credentials.lambda_update_iam_credentials_for_user_arn
}

output "lambda_find_users_to_refresh_arn" {
  description = "The Lambda ARN of Find users to update IAM credentials lambda"
  value       = module.iam_rotate_credentials.lambda_find_users_to_refresh_arn
}

output "sns_iam_rotate_credentials_result_arn" {
  description = "The SNS result ARN of topic for result IAM rotate Credential lambdas execution"
  value       = module.iam_rotate_credentials.sns_iam_rotate_credentials_result_arn
}

output "sqs_update_iam_credentials_for_user_arn" {
  description = "The ARN of SQS request IAM users credentials"
  value       = module.iam_rotate_credentials.sqs_update_iam_credentials_for_user_arn
}

output "sqs_update_iam_credentials_for_user_dead_letter_arn" {
  description = "The ARN of SQS request IAM users credentials ( dead letter )"
  value       = module.iam_rotate_credentials.sqs_update_iam_credentials_for_user_dead_letter_arn
}

output "sqs_update_iam_credentials_for_user_id" {
  description = "The URL of SQS request IAM users credentials"
  value       = module.iam_rotate_credentials.sqs_update_iam_credentials_for_user_id
}

output "sqs_update_iam_credentials_for_user_dead_letter_id" {
  description = "The URL of SQS request IAM users credentials ( dead letter )"
  value       = module.iam_rotate_credentials.sqs_update_iam_credentials_for_user_dead_letter_id
}

output "kms_ciphertext" {
  description = "The Secret used to encrypt the data"
  value       =  module.iam_rotate_credentials.kms_ciphertext
}
