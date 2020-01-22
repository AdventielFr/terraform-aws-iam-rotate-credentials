import json
import boto3
import traceback
import os
from common import Common
from common import RefreshCredentialRequest

common = Common()
account_id = common.get_account_id()
iam_client = boto3.client('iam')
ses_client = boto3.client('ses')
sqs_client = boto3.client('sqs')

def main(event, context):
    """entry point"""
    try:
        requests = find_refresh_credential_request()
        common.logger.info(f"{len(requests)} user(s) to checks")
        for request in requests:
            common.logger.info(f"Process request for user {request.user_name} ...")
            if common.is_obsolete_request(ses_client, iam_client, request):
                publish_request(request)
            else:
                common.logger.info(f"No change credentials for the user {request.user_name}")

    except Exception as e:
        stack_trace = traceback.format_exc()
        common.logger.error(stack_trace)
        common.send_message(
            f"Fail to rotate AWS iam credential {account_id}, reason : {e}", verbosity='ERROR')

def publish_request(request):
    sqs_client.send_message(
                QueueUrl = os.environ.get('AWS_SQS_REQUEST_URL'),
                MessageBody = json.dumps(request.__dict__)
            )
    common.logger.info(f"Sends a credentials renewal request for the user {request.user_name}")

def find_refresh_credential_request(marker=None):
    """find all iam users of account"""
    result = []
    response = None
    if not marker:
        response = iam_client.list_users()
    else:
        response = iam_client.list_users(Marker=marker)
    if 'Users' in response:
        for item in response['Users']:
            user_name = item['UserName']
            email = common.find_user_tag(iam_client, user_name, 'IamRotateCredentials:Email')
            if email:
                cli_time_limit = common.find_user_tag(iam_client, user_name, 'IamRotateCredentials:CliTimeLimit')
                if not cli_time_limit:
                    cli_time_limit = os.environ.get('AWS_CLI_TIME_LIMIT')
                login_profile_time_limit = common.find_user_tag(iam_client, user_name, 'IamRotateCredentials:LoginProfileTimeLimit')
                if not login_profile_time_limit:
                    login_profile_time_limit = os.environ.get('AWS_LOGIN_PROFILE_TIME_LIMIT')
                request = RefreshCredentialRequest(
                    user_name = user_name,
                    email = email,
                    cli_time_limit = int(cli_time_limit),
                    login_profile_time_limit = int(login_profile_time_limit),
                    force = False
                )
                result.append(request)
    if 'IsTruncated' in response and bool(response['IsTruncated']):
        result += find_refresh_credential_request(iam_client, marker=response['Marker'])
    return result
