import json
import boto3
import os
import traceback

from password_generator import PasswordGenerator
from common import Common
from common import RefreshCredentialRequest

common = Common()
account_id = common.get_account_id()
iam_client = boto3.client('iam')
ses_client = boto3.client('ses')
iam_resource = boto3.resource('iam')

def create_generator():
    """create a password generator"""
    generator = PasswordGenerator()
    generator.minlen = 16  
    generator.maxlen = 16  
    generator.minuchars = 2 
    generator.minlchars = 2  
    generator.minnumbers = 2 
    generator.minschars = 2  
    return generator

generator = create_generator()

def main(event, context):
    """entry point"""
    try:
        if 'Records' in event:
            for record in event['Records']:
                request = extract_request_from_record(record)
                common.logger.info(f"Process request for user {request.user_name} ...")
                if common.is_obsolete_request(ses_client, iam_client, request):
                    obsolete_login_profile_info = common.find_login_profile_info(iam_client, request)
                    obsolete_access_key_infos = list(filter(lambda x: x.is_obsolete(),common.find_access_key_infos(iam_client, request)))
                    # if login profile exist then update password 
                    if obsolete_login_profile_info:
                        update_login_profile(request, obsolete_login_profile_info)
                    # if exists access keys then re create new access keys 
                    for obsolete_access_key_info in obsolete_access_key_infos:
                        update_access_key(request, obsolete_access_key_info)
                    try_send_email(request, obsolete_login_profile_info, obsolete_access_key_infos)
    except Exception as e:
        common.logger.error(e)
        stack_trace = traceback.format_exc()
        common.logger.error(stack_trace)
        common.send_message(
            f"Fail to rotate AWS iam credential {account_id}, reason : {e}")

def extract_request_from_record(record):
    """extract refresh credential request from record"""
    payload = json.loads(record['Body'])
    return RefreshCredentialRequest(**payload)

def update_login_profile(request, login_profile_info):
    """update login profile password"""
    login_profile_info.password = generator.generate()
    login_profile = iam_resource.LoginProfile(request.user_name)
    login_profile.update(Password=login_profile_info.password,
                         PasswordResetRequired=with_password_reset_required())
    common.logger.info(f"New password generated for AWS console Access for user {request.user_name}")

def update_access_key(request, access_key_info):
    """remove and recreate access key """
    old_id = access_key_info.id
    # delete obsolete access key
    iam_client.delete_access_key(UserName=request.user_name,AccessKeyId=access_key_info.id)
    # create new access key
    response = iam_client.create_access_key(UserName=request.user_name)
    access_key_info.id = response['AccessKey']['AccessKeyId']
    access_key_info.secret = response['AccessKey']['SecretAccessKey']
    access_key_info.create_date = response['AccessKey']['CreateDate']
    common.logger.info(f'New Access/Secret Keys generated for AWS CLI for user {request.user_name} ( {old_id} -> {access_key_info.id})')

def try_send_email(request, login_profile_info, access_key_infos):
    """send email to user by AWS SES"""
    # not no action update then return 
    if not login_profile_info and len(access_key_infos) == 0:
        return
    url = f'https://{account_id}.signin.aws.amazon.com/console'
    message = f"This email is sent automatically when your credentials become obsolete for account {account_id}.\n"
    message += "\n"
    if login_profile_info:
        message += f'Your new Console Access:\n'
        message += f'\tUrl : {url}\n'
        message += f"\tLogin: {request.user_name}\n"
        message += f"\tPassword: {login_profile_info.password}\n"
        message += "\n"
        if with_password_reset_required():
            message += "For your Console Access, you will need to change your password at the next login.\n"
            message += "\n"
    if access_key_infos and len(access_key_infos)>0 : 
        for key in access_key_infos:
            message += f'Your new Command LIne Access:\n'
            message += f"\tAccess Key: {key.id}\n"
            message += f"\tSecret Key: {key.secret}\n"
    message += "\n"
    if 'CREDENTIALS_SENDED_BY' in os.environ:
        message += f"by {os.environ.get("CREDENTIALS_SENDED_BY")}.\n"
    ses_client.send_email(
        Source = os.environ.get('AWS_SES_EMAIL_FROM'),
        Destination = {'ToAddresses': [request.email]},
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
    common.logger.info(f'New credentials sended to {request.email} for user {request.user_name}.')

def with_password_reset_required():
    env = os.environ.get('AWS_LOGIN_PROFILE_PASSWORD_RESET_REQUIRED')
    if not env:
        return True
    return env.lower().strip() in ['true', '1']

