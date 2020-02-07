#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import boto3
import traceback
import os
import datetime
import time 
from common import Common
from common import RefreshCredentialRequest

common = Common()
account_id = common.get_account_id()
iam_client = boto3.client('iam')
ses_client = boto3.client('ses')
sqs_client = boto3.client('sqs')

DEFAULT_LIMIT = 60

def main(event, context):
    """entry point"""
    try:
        credential_report = get_credential_report()
        find_refresh_credential_request(credential_report)
   
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

def find_obsolete_access_key_ids(user_name, marker=None):
    """find all active and obsolete access_key of user if exists """
    cli_time_limit = common.find_user_tag(iam_client, user_name, 'IamRotateCredentials:CliTimeLimit')
    if not cli_time_limit:
        cli_time_limit = os.environ.get('AWS_CLI_TIME_LIMIT')
    result = []
    try:
        response = None
        if not marker:
            response = iam_client.list_access_keys(UserName=user_name)
        else:
            response = iam_client.list_access_keys(UserName=user_name, Marker=marker)
        if 'AccessKeyMetadata' in response:
            for item in filter(lambda x: x['Status'] == 'Active', response['AccessKeyMetadata']):
                if is_obsolete(item["CreateDate"],common.to_int(cli_time_limit, DEFAULT_LIMIT)):
                    result.append(item['AccessKeyId'])
        if 'IsTruncated' in response and bool(response['IsTruncated']):
            result += find_access_keys(request,
                                   marker=response['Marker'])
        return result
    except iam_client.exceptions.NoSuchEntityException:
        return result

def is_obsolete_login_profile(user_name, credential_report):
    """find login profile if exist and if login profile is obsolete"""
    login_profile_time_limit = common.find_user_tag(iam_client, user_name, 'IamRotateCredentials:LoginProfileTimeLimit')
    if not login_profile_time_limit:
        login_profile_time_limit = os.environ.get('AWS_LOGIN_PROFILE_TIME_LIMIT')
    try:
        response = iam_client.get_login_profile(UserName=user_name)
        if 'LoginProfile' in response:
            credential_report_info = next((item for item in credential_report if item['user'] == user_name), None)
            if credential_report_info:
                password_last_changed = credential_report_info["password_last_changed"].split('T')[0]
                password_last_changed = datetime.datetime.strptime(password_last_changed, "%Y-%m-%d")
                return is_obsolete(password_last_changed, common.to_int(login_profile_time_limit, DEFAULT_LIMIT))
            return False
        return None
    except iam_client.exceptions.NoSuchEntityException:
        return False

def is_obsolete(date, delta):
    limit_date = (date + datetime.timedelta(days=delta)).date()
    return datetime.date.today() > limit_date

def find_refresh_credential_request(credential_report, marker=None):
    """find all iam users of account"""
    response = None
    if not marker:
        response = iam_client.list_users()
    else:
        response = iam_client.list_users(Marker=marker)
    if 'Users' in response:
        for item in response['Users']:
            user_name = item['UserName']
            common.logger.info(f"Process request for user {user_name} ...")
            email = common.find_user_tag(iam_client, user_name, 'IamRotateCredentials:Email')
            if email:
                if common.is_valid_email(ses_client, user_name, email):
                    refresh_login_profile = is_obsolete_login_profile(user_name, credential_report)
                    refresh_access_keys = find_obsolete_access_key_ids(user_name)
                    if refresh_login_profile or len(refresh_access_keys)>0:
                        request = RefreshCredentialRequest(
                            user_name = user_name,
                            login_profile = refresh_login_profile,
                            access_key_ids = refresh_access_keys,
                            force = False
                        )
                        publish_request(request)
                    else:
                        common.logger.info(f"User {user_name} excluded, reason: The credentials are not obsolete")
            else:
                common.logger.info(f"User {user_name} excluded, reason: 'IamRotateCredentials:Email' tag not exist for user")
    if 'IsTruncated' in response and bool(response['IsTruncated']):
        find_refresh_credential_request(iam_client, marker=response['Marker'])

def get_credential_report():
    response = iam_client.generate_credential_report()
    if response['State'] == 'COMPLETE' :
        credential_report = []
        response = iam_client.get_credential_report()
        report = response["Content"]
        lines = report.splitlines()
        keys = lines[0].decode("utf-8").split(',')
        for i in range(1, len(lines)):
            item = {}
            data = lines[i].decode("utf-8").split(',')
            for j in range(0, len(keys)):
                item[keys[j]]= data[j]
                credential_report.append(item)
        return credential_report
    else:
        time.sleep(2)
        return get_credential_report()
