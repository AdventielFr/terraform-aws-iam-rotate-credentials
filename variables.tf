variable "aws_region" {
  description = "aws region to deploy (only aws region with AWS SES service deployed)"
  type        = string
}

variable "function_timeout" {
  description = "The amount of time your Lambda Functions has to run in seconds."
  default     = 300
  type        = number
}

variable "aws_ses_email_from" {
  description = "email used to send emails to users when their credentials change."
  type        = string
}

variable "cloudwatch_log_retention" {
  description = "The cloudwatch log retention ( default 7 days )."
  default     = 7
  type        = number
}

variable "scan_alarm_clock" {
  description = "The time between two scan to search for expired certificates ( in minutes default 1440 = 1 days)"
  type        = number
  default     = 1440
}

variable "aws_login_profile_password_reset_required" {
  description = "Requires that the console password be changed by the user at the next login."
  type        = bool
  default     = true
}

variable "aws_login_profile_time_limit" {
  description = "Maximum duration for an access with login profile (expressed in days)."
  type        = number
  default     = 60
}

variable "aws_cli_time_limit" {
  description = "Maximum duration for an access with AWS CLI (expressed in days)."
  type        = number
  default     = 60
}

variable "aws_account_name" {
  description ="Name of Aws Account ( use in email sender to user where credentials are obsoletes )"
  type = string
  default = "<your aws acccount name>"
}

variable "tags" {
  description = "The tags of all resources created"
  type        = map
  default     = {}
}

variable "credentials_sended_by" {
  description = "The sender of renewal credentials emails"
  type        = string
  default     = "<your ops teams>"
}

variable "kms_ciphertext" {
  description = "Data to be encrypted"
  type  = string
  default = ""
}
