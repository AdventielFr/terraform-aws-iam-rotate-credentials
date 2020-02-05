
data "aws_iam_policy_document" "find_users_to_refresh" {

  statement {
    sid       = "AllowSESAccess"
    effect    = "Allow"
    resources = ["*"]

    actions = [
      "ses:ListIdentities",
      "ses:GetIdentityVerificationAttributes"
    ]
  }

  statement {
    sid    = "AllowSQSPermissions"
    effect = "Allow"
    resources = [
      aws_sqs_queue.update_iam_credentials_for_user.arn
    ]

    actions = [
      "sqs:SendMessage",
    ]
  }

  statement {
    sid    = "AllowKMSPermissions"
    effect = "Allow"
    resources = [
      aws_kms_key.iam_rotate_credentials.arn
    ]
    actions = [
      "kms:GenerateDataKey",
      "kms:Decrypt"
    ]
  }

  statement {
    sid       = "AllowIAMAccess"
    effect    = "Allow"
    resources = ["*"]

    actions = [
      "iam:GetLoginProfile",
      "iam:GetUser",
      "iam:ListAccessKeys",
      "iam:ListUsers",
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
    sid       = "AllowCloudwatck"
    effect    = "Allow"
    resources = ["*"]

    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
  }
}

data "aws_iam_policy_document" "update_iam_credentials_for_user" {

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
    sid    = "AllowKMSPermissions"
    effect = "Allow"
    resources = [
      aws_kms_key.iam_rotate_credentials.arn
    ]
    actions = [
      "kms:Decrypt"
    ]
  }

  statement {
    sid    = "AllowSQSPermissions"
    effect = "Allow"
    resources = [
      aws_sqs_queue.update_iam_credentials_for_user.arn
    ]

    actions = [
      "sqs:ChangeMessageVisibility",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "sqs:SendMessage",
      "sqs:ReceiveMessage"
    ]
  }

  statement {
    sid       = "AllowCreatingLogGroups"
    effect    = "Allow"
    resources = ["arn:aws:logs:${var.aws_region}:*:*"]
    actions   = ["logs:CreateLogGroup"]
  }

  statement {
    sid       = "AllowWritingLogs"
    effect    = "Allow"
    resources = ["arn:aws:logs:${var.aws_region}:*:log-group:/aws/lambda/*:*"]

    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
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

resource "aws_iam_policy" "find_users_to_refresh" {
  name   = "${local.lambda_find_users_to_refresh_name}-policy"
  policy = data.aws_iam_policy_document.find_users_to_refresh.json
}

resource "aws_iam_policy" "update_iam_credentials_for_user" {
  name   = "${local.lambda_update_iam_credentials_for_user_name}-policy"
  policy = data.aws_iam_policy_document.update_iam_credentials_for_user.json
}

resource "aws_iam_role" "find_users_to_refresh" {
  name               = "${local.lambda_find_users_to_refresh_name}-role"
  description        = "Set of access policies granted to lambda ${local.lambda_find_users_to_refresh_name}"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": [
          "lambda.amazonaws.com"
        ]
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
  tags               = merge(local.tags, map("Lambda", local.lambda_find_users_to_refresh_name))
}

resource "aws_iam_role" "update_iam_credentials_for_user" {
  name               = "${local.lambda_update_iam_credentials_for_user_name}-role"
  description        = "Set of access policies granted to lambda ${local.lambda_update_iam_credentials_for_user_name}"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": [
          "lambda.amazonaws.com"
        ]
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
  tags               = merge(local.tags, map("Lambda", local.lambda_update_iam_credentials_for_user_name))
}

resource "aws_iam_role_policy_attachment" "update_iam_credentials_for_user" {
  policy_arn = aws_iam_policy.update_iam_credentials_for_user.arn
  role       = aws_iam_role.update_iam_credentials_for_user.name
}

resource "aws_iam_role_policy_attachment" "find_users_to_refresh" {
  policy_arn = aws_iam_policy.find_users_to_refresh.arn
  role       = aws_iam_role.find_users_to_refresh.name
}

data "aws_iam_policy_document" "sqs_policy" {
  policy_id = "${local.sqs_arn}/SQSDefaultPolicy"

  statement {
    effect = "Allow"

    principals {
      type = "AWS"
      identifiers = [
        "*"
      ]
    }

    actions = [
      "SQS:SendMessage",
    ]

    resources = [
      local.sqs_arn,
    ]

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"

      values = [
        local.lambda_find_users_to_refresh_arn
      ]
    }
  }

  statement {
    effect = "Allow"

    principals {
      type = "AWS"
      identifiers = [
        "*"
      ]
    }

    actions = [
      "sqs:ChangeMessageVisibility",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "sqs:DeleteMessage",
      "sqs:ReceiveMessage"
    ]

    resources = [
      local.sqs_arn,
    ]

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"

      values = [
        local.lambda_update_iam_credentials_for_user_arn
      ]
    }
  }
}