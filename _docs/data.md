## Inputs

| Name | Description | Type | Default |
|------|-------------|:----:|:-----:|
| aws\_cli\_time\_limit | Maximum duration for an access with AWS CLI (expressed in days). | number | 60 |
| aws\_login\_profile\_password\_reset\_required | Requires that the console password be changed by the user at the next login. | bool | true |
| aws\_login\_profile\_time\_limit | Maximum duration for an access with login profile (expressed in days). | number | 60 |
| aws\_region | aws region to deploy (only aws region with AWS SES service deployed) | string | n/a |
| aws\_ses\_email\_from | email used to send emails to users when their credentials change. | string | n/a |
| cloudwatch\_log\_retention | The cloudwatch log retention ( default 7 days ). | number | 7 |
| credentials\_sended\_by | The sender of renewal credentials emails | string | "ops team" |
| function\_timeout | The amount of time your Lambda Functions has to run in seconds. | number | 300 |
| kms\_ciphertext | Data to be encrypted | string | "" |
| scan\_alarm\_clock | The time between two scan to search for expired certificates ( in minutes default 1440 = 1 days) | number | 1440 |
| tags | The tags of all resources created | map | {} |

## Outputs

| Name | Description |
|------|-------------|
| kms\_ciphertext | The Secret used to encrypt the data |
| lambda\_find\_users\_to\_refresh\_arn | The Lambda ARN of Find users to update IAM credentials lambda |
| lambda\_update\_iam\_credentials\_for\_user\_arn | The Lambda ARN of Update IAM credentials lambda |
| sns\_iam\_rotate\_credentials\_result\_arn | The SNS result ARN of topic for result IAM rotate Credential lambdas execution |
| sqs\_update\_iam\_credentials\_for\_user\_arn | The ARN of SQS request IAM users credentials |
| sqs\_update\_iam\_credentials\_for\_user\_dead\_letter\_arn | The ARN of SQS request IAM users credentials ( dead letter ) |
| sqs\_update\_iam\_credentials\_for\_user\_dead\_letter\_id | The URL of SQS request IAM users credentials ( dead letter ) |
| sqs\_update\_iam\_credentials\_for\_user\_id | The URL of SQS request IAM users credentials |
