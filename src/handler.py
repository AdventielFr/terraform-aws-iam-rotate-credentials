import json
import boto3
import botocore
import logging
import datetime
import os
import shutil
import re
import traceback
from password_generator import PasswordGenerator

logger = logging.getLogger()
logger.setLevel(logging.INFO)

AWS_LOGIN_PROFILE_TIME_LIMIT = os.environ.get('AWS_LOGIN_PROFILE_TIME_LIMIT')
AWS_CLI_TIME_LIMIT = os.environ.get('AWS_CLI_TIME_LIMIT')
AWS_SNS_RESULT_ARN = os.environ.get('AWS_SNS_RESULT_ARN')
AWS_SES_EMAIL_FROM = os.environ.get('AWS_SES_EMAIL_FROM')

class UserInfo():
    def __init__(self, user_name, user_id, email_iam_rotate_credential):
        self._user_name = user_name
        self._user_id = user_id
        self._login_profile = None
        self._access_keys = None
        self._email_iam_rotate_credential = email_iam_rotate_credential

    def get_user_name(self):
        return self._user_name

    def set_user_name(self, value):
        self._user_name = value

    def get_login_profile(self):
        return self._login_profile

    def set_login_profile(self, value):
        self._login_profile = value

    def get_access_keys(self):
        return self._access_keys

    def set_access_keys(self, value):
        self._access_keys = value

    def get_force_refresh(self):
        return self._force_refresh

    def set_force_refresh(self, value):
        self._force_refresh = value

    def get_email_iam_rotate_credential(self):
        return self._email_iam_rotate_credential

    def set_email_iam_rotate_credential(self, value):
        self._email_iam_rotate_credential = value

    user_name = property(get_user_name, set_user_name)
    login_profile = property(get_login_profile, set_login_profile)
    access_keys = property(get_access_keys, set_access_keys)
    force_refresh = property(get_force_refresh, set_force_refresh)
    email_iam_rotate_credential = property(get_email_iam_rotate_credential,
                                           set_email_iam_rotate_credential)


class AccessKeyInfo():
    def __init__(self, id, create_date):
        self._id = id
        self._secret = None
        self._create_date = create_date

    def get_id(self):
        return self._id

    def set_id(self, value):
        self._id = value

    def get_secret(self):
        return self._secret

    def set_secret(self, value):
        self._secret = value

    def get_create_date(self):
        return self._create_date

    def set_create_date(self, value):
        self._create_date = value

    id = property(get_id, set_id)
    secret = property(get_secret, set_secret)
    create_date = property(get_create_date, set_create_date)


class LoginProfileInfo():
    def __init__(self, create_date):
        self._password = None
        self._create_date = create_date

    def get_password(self):
        return self._password

    def set_password(self, value):
        self._password = value

    def get_create_date(self):
        return self._create_date

    def set_create_date(self, value):
        self._create_date = value

    password = property(get_password, set_password)
    create_date = property(get_create_date, set_create_date)


def create_generator():
    """create a password generator"""
    generator = PasswordGenerator()
    generator.minlen = 16  # (Optional)
    generator.maxlen = 16  # (Optional)
    generator.minuchars = 1  # (Optional)
    generator.minlchars = 1  # (Optional)
    generator.minnumbers = 1  # (Optional)
    generator.minschars = 1  # (Optional)
    return generator


def main(event, context):
    """entry point"""
    account_id = ''
    try:
        account_id = boto3.client('sts').get_caller_identity().get('Account')
        iam_client = boto3.client('iam')
        ses_client = boto3.client('ses')
        sns_client = boto3.client('sns')
        users = find_users(iam_client, ses_client)
        generator = create_generator()
        resource = boto3.resource('iam')

        # scan users
        for user in users:
            user.login_profile = find_login_profile(iam_client, user.user_name)
            user.access_keys = find_access_keys(iam_client, user.user_name)
            if try_update_user(iam_client, resource, user, generator):
                send_email(ses_client, user, account_id)
        send_message(
            sns_client, f"Success to rotate AWS iam credential {account_id}.")
    except Exception as e:
        logger.error(e)
        stack_trace = traceback.format_exc()
        logger.error(stack_trace)
        send_message(
            sns_client,
            f"Fail to rotate AWS iam credential {account_id}, reason : {e}")

def with_password_reset_required():
    env = os.environ.get('AWS_LOGIN_PROFILE_PASSWORD_RESET_REQUIRED')
    if not env:
        return True
    return env.lower().strip() in ['true', '1']

def try_update_user(client, resource, user, generator):
    """update user if login profile or access_keys is obsolete"""
    result = False
    if user.login_profile and is_obsolete(user.login_profile.create_date,
                                          is_profile=True):
        update_login_profile(resource, user, generator)
        result = True
    for item in user.access_keys:
        if is_obsolete(item.create_date, is_profile=False):
            update_access_key(client, user, item)
            result = True
    return result


def update_login_profile(resource, user, generator):
    """update login profile password"""
    user.login_profile.password = generator.generate()
    login_profile = resource.LoginProfile(user.user_name)
    login_profile.update(Password=user.login_profile.password,
                         PasswordResetRequired=with_password_reset_required())


def update_access_key(client, user, access_key):
    """remove and recreate access key """
    logger.info(
        f'Try update access key user: {user.user_name} id: {access_key.id} ...'
    )
    old_id = access_key.id
    # delete obsolete access key
    client.delete_access_key(UserName=user.user_name,
                             AccessKeyId=access_key.id)
    # create new access key
    response = client.create_access_key(UserName=user.user_name)
    access_key.id = response['AccessKey']['AccessKeyId']
    access_key.secret = response['AccessKey']['SecretAccessKey']
    access_key.create_date = response['AccessKey']['CreateDate']
    logger.info(
        f'Update the access key successfully user: {user.user_name} id: {old_id} to {access_key.id}'
    )


def send_message(sns_client, message):
    """send message to sns topic"""
    logger.info('Send result message ....')
    return sns_client.publish(TopicArn=AWS_SNS_RESULT_ARN, Message=message)


def send_email(ses_client, user, account_id):
    """send email to user"""
    logger.info(
        f'Try send mail to ({user.user_name}) : {user.email_iam_rotate_credential} ...'
    )
    url = f'https://{account_id}.signin.aws.amazon.com/console'
    message = f"This email is sent automatically when your credentials become obsolete for account {account_id}.\n"
    message += "\n"
    if user.login_profile:
        message += f'Your new Console Access:\n'
        message += f'\tUrl : {url}\n'
        message += f"\tLogin: {user.user_name}\n"
        message += f"\tpassword: {user.login_profile.password}\n"
        message += "\n"
        message += "For your Console Access, you will need to change your password at the next login.\n"
        message += "\n"
    for key in user.access_keys:
        message += f'Your new CLI Access:\n'
        message += f"\tAccess Key: {key.id}\n"
        message += f"\tSecret Key: {key.secret}\n"
    message += "\n"
    message += "by OPS Team.\n"
    ses_client.send_email(
        Source=AWS_SES_EMAIL_FROM,
        Destination={'ToAddresses': [user.email_iam_rotate_credential]},
        Message={
            'Subject': {
                'Data':
                f'Update Amazon WebService credentials for {account_id}'
            },
            'Body': {
                'Text': {
                    'Data': message
                }
            }
        })
    logger.info(f'Sending the mail for {user.user_name} successfully.')


def is_obsolete(date, is_profile=False):
    limit = AWS_LOGIN_PROFILE_TIME_LIMIT if is_profile else AWS_CLI_TIME_LIMIT
    limit_date = date + datetime.timedelta(days=int(limit))
    return datetime.datetime.now() > limit_date.replace(tzinfo=None)


def find_access_keys(iam_client, user_name, marker=None):
    """find all active access_key of user if exists"""
    result = []
    try:
        response = None
        if not marker:
            response = iam_client.list_access_keys(UserName=user_name)
        else:
            response = iam_client.list_access_keys(UserName=user_name,
                                                   Marker=marker)
        if 'AccessKeyMetadata' in response:
            for item in filter(lambda x: x['Status'] == 'Active',
                               response['AccessKeyMetadata']):
                result.append(
                    AccessKeyInfo(item['AccessKeyId'], item['CreateDate']))
        if 'IsTruncated' in response and bool(response['IsTruncated']):
            result += find_access_keys(iam_client,
                                       user_name,
                                       marker=response['Marker'])
        return result
    except iam_client.exceptions.NoSuchEntityException:
        return result


def find_login_profile(iam_client, user_name):
    """find login profile if exist"""
    result = None
    try:
        response = iam_client.get_login_profile(UserName=user_name)
        if 'LoginProfile' in response:
            result = LoginProfileInfo(response['LoginProfile']['CreateDate'])
        return result
    except iam_client.exceptions.NoSuchEntityException:
        return result


def find_iam_rotate_credential_user_email(iam_client, ses_client, user_name, marker=None):
    """ find IAM rotate credential tag of user """
    response = None
    if not marker:
        response = iam_client.list_user_tags(UserName=user_name)
    else:
        response = iam_client.list_user_tags(UserName=user_name, Marker=marker)
    if 'Tags' in response:
        tag = next((x for x in response['Tags']
                    if x['Key'] == 'IamRotateCredentialEmail'), None)
        if tag and is_iam_rotate_credential_valid_email(ses_client, tag['Value']):
            return tag['Value']
    if 'IsTruncated' in response and bool(response['IsTruncated']):
        return find_iam_rotate_credential_user_email(iam_client,
                                                     ses_client,
                                                     user_name,
                                                     marker=response['Marker'])
    return None


def is_iam_rotate_credential_valid_email(ses_client, email):
    regex = '^[a-zA-Z0-9_.+-]+@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)$'
    match = re.match(regex, email)
    if not match:
        return False
    # test mail
    logger.info(f'Check AWS SES Status for email {email}')
    response = ses_client.get_identity_verification_attributes(Identities=[
                                                               email])
    status = None
    if email in response['VerificationAttributes']:
        status = response['VerificationAttributes'][email][
            'VerificationStatus']
        if status == 'Success':
            logger.info(f'User mail {email} validated by AWS SES.')
            return True
        else:
            logger.info(
                f'User mail {email} not validated by AWS SES ( status = {status} ).'
            )

    # test domain
    domain = match.group(1)
    logger.info(f'Check AWS SES Status for domain {domain}')
    response = ses_client.get_identity_verification_attributes(
        Identities=[match.group(1)])
    if domain in response['VerificationAttributes']:
        status = response['VerificationAttributes'][domain][
            'VerificationStatus']
    if status == 'Success':
        logger.info(f'User mail {email} validated by AWS SES ( domain ).')
        return True
    else:
        logger.info(
            f'User mail {email} not domain validated by AWS SES ( status = {status} ).'
        )

    return False


def find_users(iam_client, ses_client, marker=None):
    """find all iam users of account"""
    result = []
    response = None
    if not marker:
        response = iam_client.list_users()
    else:
        response = iam_client.list_users(Marker=marker)
    if 'Users' in response:
        for item in response['Users']:
            email = find_iam_rotate_credential_user_email(
                iam_client, ses_client, item['UserName'])
            if email:
                user = UserInfo(item['UserName'], item['UserId'], email)
                result.append(user)
    if 'IsTruncated' in response and bool(response['IsTruncated']):
        result += find_users(iam_client, ses_client, marker=response['Marker'])
    return result
