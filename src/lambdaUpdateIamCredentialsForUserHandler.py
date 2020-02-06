#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import boto3
import os
import traceback
import random

from password_generator import PasswordGenerator
from common import Common
from common import RefreshCredentialRequest

common = Common()
account_id = common.get_account_id()
iam_client = boto3.client('iam')
ses_client = boto3.client('ses')
iam_resource = boto3.resource('iam')

def create_password():
    response = iam_client.get_account_password_policy()
    password_len = 16
    password_src_lower_char = "abcdefghijklmnopqrstuvwxyz"
    password_src_upper_char = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    password_src_number = "01234567890"
    password_src_symbol = "!@#$%^&*()_+-=[]|'"
    password_src = password_src_lower_char + password_src_upper_char + password_src_number + password_src_symbol
    if 'PasswordPolicy' in response:
        password_policy = response['PasswordPolicy']
        if not password_policy['RequireSymbols']:
            password_src = password_src.replace(password_src_symbol,"")
        password_len = password_policy['MinimumPasswordLength']
    return "".join(random.sample(password_src, password_len ))

def main(event, context):
    """entry point"""
    try:
        if 'Records' in event:
            for record in event['Records']:
                request = extract_request_from_record(record)
                common.logger.info(f"Process request for user {request.user_name} ...")
                email = common.find_user_tag(iam_client, request.user_name, 'IamRotateCredentials:Email')
                if email:
                    if common.is_valid_email(ses_client, request.user_name, email):
                        new_password_login_profile = None
                        if request.login_profile or request.force:
                            new_password_login_profile = update_login_profile(request.user_name)
                        new_access_keys = []
                        access_key_ids = request.access_key_ids
                        if request.force:
                            refresh_access_keys = find_all_access_key_ids(request.user_name)
                        for access_key_id in access_key_ids:
                            new_access_key = update_access_key(request.user_name, access_key_id)
                            new_access_keys.append(new_access_key)
                        send_email(request.user_name, email, new_password_login_profile, new_access_keys)
                    else:
                        raise ValueError(f"Invalid mail for user {request.user_name} ")
                else:
                    raise ValueError(f"'IamRotateCredentials:Email' tag not exist for user {request.user_name}")
    except Exception as e:
        common.logger.error(e)
        stack_trace = traceback.format_exc()
        common.logger.error(stack_trace)
        common.send_message(
            f"Fail to rotate AWS iam credential {account_id}, reason : {e}")

def extract_request_from_record(record):
    """extract refresh credential request from record"""
    payload = json.loads(record['body'])
    request = RefreshCredentialRequest(**payload)
    return request

def update_login_profile(user_name):
    """update login profile password"""
    new_password = create_password()
    login_profile = iam_resource.LoginProfile(user_name)
    login_profile.update(Password=new_password,
                         PasswordResetRequired=with_password_reset_required())
    common.logger.info(f"New password generated for AWS console Access for user {user_name}")
    return new_password

def update_access_key(user_name, old_access_key):
    """remove and recreate access key """
    # delete obsolete access key
    iam_client.delete_access_key(UserName=user_name, AccessKeyId=old_access_key)

    # create new access key
    response = iam_client.create_access_key(UserName=user_name)
    new_access_key = response['AccessKey']['AccessKeyId']
    new_secret_key = response['AccessKey']['SecretAccessKey']
    common.logger.info(f'New Access/Secret Keys generated for AWS CLI for user {user_name} ( {old_access_key} -> {new_access_key})')
    result = {}
    result["Key"] = new_access_key
    result["Secret"] = new_secret_key
    return result

def send_email(user_name, email, new_password_login_profile, new_access_keys):
    """send email to user by AWS SES"""
    # not no action update then return 
    url = f'https://{account_id}.signin.aws.amazon.com/console'
    account_info = ""
    if 'AWS_ACCOUNT_NAME' in os.environ:
        account_info += os.environ.get('AWS_ACCOUNT_NAME')
        account_info += ' - '
    account_info += account_id

    message = f"This email is sent automatically when your credentials become obsolete for account {account_info}.\n"
    message += "\n"
    if new_password_login_profile:
        message += f'Your new Console Access:\n'
        message += f'\tUrl : {url}\n'
        message += f"\tLogin: {user_name}\n"
        message += f"\tPassword: {new_password_login_profile}\n"
        message += "\n"
        if with_password_reset_required():
            message += "For your Console Access, you will need to change your password at the next login.\n"
            message += "\n"
    if new_access_keys and len(new_access_keys)>0 : 
        for key in access_key_infos:
            message += 'Your new Command LIne Access:\n'
            message += f'\tAccess Key: {key["Key"]}\n'
            message += f'\tSecret Key: {key["Secret"]}\n'
    message += "\n"
    if 'CREDENTIALS_SENDED_BY' in os.environ:
        credentials_sended_by = os.environ.get("CREDENTIALS_SENDED_BY")
        message += f"by {credentials_sended_by}.\n"
    ses_client.send_email(
        Source = os.environ.get('AWS_SES_EMAIL_FROM'),
        Destination = {'ToAddresses': [email]},
        Message={
            'Subject': {
                'Data':
                f'Update Amazon WebService credentials for {account_id} by IAMRotateCredentials'
            },
            'Body': {
                'Text': {
                    'Data': message
                }
            }
        })
    common.logger.info(f'New credentials sended to {email} for user {user_name}.')

def with_password_reset_required():
    env = os.environ.get('AWS_LOGIN_PROFILE_PASSWORD_RESET_REQUIRED')
    if not env:
        return True
    return env.lower().strip() in ['true', '1']


def find_all_access_key_ids(user_name, marker=None):
    """find all active and obsolete access_key of user if exists """
    result = []
    response = None
    if not marker:
        response = iam_client.list_access_keys(UserName=user_name)
    else:
        response = iam_client.list_access_keys(UserName=user_name, Marker=marker)
        if 'AccessKeyMetadata' in response:
            for item in filter(lambda x: x['Status'] == 'Active', response['AccessKeyMetadata']):
                result.append(item['AccessKeyId'])

        if 'IsTruncated' in response and bool(response['IsTruncated']):
            result += find_all_access_keys(request, marker=response['Marker'])
        return result
