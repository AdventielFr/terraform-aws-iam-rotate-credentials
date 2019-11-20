
provider "aws" {
  region = "eu-west-1"
}

module "iam_rotate_credentials" {
  source                       = "../"
  aws_region                   = "eu-west-1"
  aws_ses_email_from           = "gwendall.garnier@adventiel.fr"
  aws_login_profile_time_limit = 10
  aws_cli_time_limit           = 15
}

output "lambda_arn" {
  description = "The Lambda ARN"
  value       = module.iam_rotate_credentials.lambda_arn
}

output "sns_result_arn" {
  description = "The SNS result ARN of topic for result of renew cerificates"
  value       = module.iam_rotate_credentials.sns_result_arn
}

