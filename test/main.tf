
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

output "lambda_update_iam_credentials_arn" {
  description = "The Lambda ARN of Update IAM credentials lambda"
  value       = module.iam_rotate_credentials.lambda_update_iam_credentials_arn
}

output "lambda_find_users_to_update_iam_credentials_arn" {
  description = "The Lambda ARN of Find users to update IAM credentials lambda"
  value       = module.iam_rotate_credentials.lambda_find_users_to_update_iam_credentials_arn
}

output "sns_result_arn" {
  description = "The SNS result ARN of topic for result of renew cerificates"
  value       = module.iam_rotate_credentials.sns_result_arn
}

