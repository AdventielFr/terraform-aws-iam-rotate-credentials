import re
import os
import logging
import boto3
import datetime
from abc import ABC, abstractmethod

class RefreshCredentialRequest(object):
    def __init__(self, **kwargs):
        self.user_name = None
        self.force = False
        self.email = None
        self.cli_time_limit = None
        self.login_profile_time_limit = None
        self.__dict__.update(kwargs)
        if not self.user_name:
            raise ValueError("user_name is required")
        if not self.force:
            if not self.cli_time_limit:
                raise ValueError("cli_time_limit is required")
            if not self.login_profile_time_limit:
                raise ValueError("login_profile_time_limit is required")        

class AuditableInfo(ABC):
    def __init__(self, create_date, request):
        self.request = request
        self.create_date = create_date
        if not create_date:
            raise ValueError("create_date is required")
        if not request:
            raise ValueError("request is required")
        
    @abstractmethod
    def is_obsolete(self):
        pass

    def _is_obsolete(self, delta):
        if self.request.force:
            return True
        limit_date = (self.create_date + datetime.timedelta(days=delta)).date()
        return datetime.date.today() > limit_date

 class LoginProfileInfo(AuditableInfo):
    def __init__(self, create_date, request):
        super(LoginProfileInfo, self).__init__(create_date, request)
        self.password = None
    
    def is_obsolete(self):
        return self._is_obsolete(self.request.login_profile_time_limit)

class AccessKeyInfo(AuditableInfo):
    def __init__(self, id, create_date, request):
        super(AccessKeyInfo, self).__init__(create_date, request)
        self.id = id
        self.secret = None

    def is_obsolete(self):
        return self._is_obsolete(self.request.cli_time_limit)
        
class Common(object):

    def __init__(self):
        self._logger = logger = logging.getLogger()
        self._logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s : %(name)s : %(levelname)s : %(message)s')
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        self._logger.addHandler(ch)

    @property
    def logger(self):
        return self._logger

    @logger.getter
    def get_logger(self):
        """get logger"""
        return self._logger

    def send_message(self, message, verbosity = 'INFO'):
        """send message to sns topic"""
        sns_client = boto3.client('sns')
        aws_sns_result_arn = os.environ.get('AWS_SNS_RESULT_ARN')
        return sns_client.publish(TopicArn=aws_sns_result_arn, Message=f'[{verbosity}]:{message}')

    def get_account_id(self):
        return boto3.client('sts').get_caller_identity().get('Account')

    def is_obsolete_request(self, ses_client, iam_client, request):
        if self.is_valid_email(ses_client, request):
            login_profile_info = self.find_login_profile_info(iam_client, request)
            if login_profile_info and login_profile_info.is_obsolete():
                return True
            access_key_infos = list(filter(lambda x: x.is_obsolete(),self.find_access_key_infos(iam_client, request)))
            return len(access_key_infos)>0
        else:
            False

    def is_known_ses_email_for_user(self, ses_client, request):
        self.logger.info(f'Check AWS SES email status ("{request.email}") for user "{request.user_name}"')
        response = ses_client.get_identity_verification_attributes(Identities=[request.email])
        status = None
        if request.email in response['VerificationAttributes']:
            status = response['VerificationAttributes'][request.email][
                'VerificationStatus']
            if status == 'Success':
                self.logger.info(f'User {request.user_name} with email {request.email} is validated by AWS SES ( AWS SES email = {request.email}, status = {status} ).')
                return True
            else:
                message = f'User {request.user_name} with email {request.email} is not validated by AWS SES ( AWS SES email = {request.email}, status = {status} ).'
                self.logger.warn(message)
                self.send_message(message,verbosity='WARN')
        return False

    def is_known_ses_domain_for_user(self, ses_client, request, domain):
        self.logger.info(f'Check AWS SES domain status ("{domain}") for user "{request.user_name}"')
        response = ses_client.get_identity_verification_attributes(Identities=[domain])
        if domain in response['VerificationAttributes']:
            status = response['VerificationAttributes'][domain][
                'VerificationStatus']
        if status == 'Success':
            self.logger.info(f'User {request.user_name} with email {request.email} is validated by AWS SES ( AWS SES domain = {domain}, status = {status} ).')
            return True
        else:
            message = f'User mail {request.user_name} with email {request.email} is not validated by AWS SES ( AWS SES domain = {domain}, status = {status} ).'
            self.logger.warn(message)
            self.send_message(message,verbosity='WARN')
        return False
    
    def is_valid_email(self, ses_client, request):
        match = re.match(r"^[a-zA-Z0-9_.+-]+@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)$", request.email)
        if not match:
            message = f'For user {request.user_name}, {request.email} is not a valid email.'
            self.logger.warn(message)
            self.send_message(message,verbosity='WARN')
            return False
    
        # test mail
        is_valid = self.is_known_ses_email_for_user(ses_client, request)
        if is_valid:
            return True

        # test domain
        domain = match.group(1)
        is_valid = self.is_known_ses_domain_for_user(ses_client, request, domain)
        if is_valid:
            return True

        message = f'User {request.user_name} with email {request.email} is not validated by AWS SES.'
        self.logger.warn(message)
        self.send_message(message, verbosity='WARN')
        return False

    def find_access_key_infos(self, iam_client, request, marker=None):
        """find all active access_key of user if exists and if access_key is obsolete"""
        result = []
        try:
            response = None
            if not marker:
                response = iam_client.list_access_keys(UserName=request.user_name)
            else:
                response = iam_client.list_access_keys(UserName=request.user_name, Marker=marker)
            if 'AccessKeyMetadata' in response:
                for item in filter(lambda x: x['Status'] == 'Active', response['AccessKeyMetadata']):
                    result.append(
                        AccessKeyInfo(
                            item['AccessKeyId'], 
                            item['CreateDate'],
                            request
                        )
                    )
            if 'IsTruncated' in response and bool(response['IsTruncated']):
                result += find_access_keys(request,
                                       marker=response['Marker'])
            return result
        except iam_client.exceptions.NoSuchEntityException:
            return result

    def find_login_profile_info(self, iam_client, request):
        """find login profile if exist and if login profile is obsolete"""
        try:
            response = iam_client.get_login_profile(UserName=request.user_name)
            if 'LoginProfile' in response:
                return LoginProfileInfo(response['LoginProfile']['CreateDate'], request)
            return None
        except iam_client.exceptions.NoSuchEntityException:
            return None

    def find_user_tag(self, iam_client, user_name, tag_key, marker=None):
        response = None
        if not marker:
            response = iam_client.list_user_tags(UserName=user_name)
        else:
            response = iam_client.list_user_tags(UserName=user_name, Marker=marker)
        if 'Tags' in response:
            tag = next((x for x in response['Tags'] if x['Key'] == tag_key), None)
            if tag:
                return tag['Value']
        if 'IsTruncated' in response and bool(response['IsTruncated']):
            return find_user_tag(user_name, tag_key, marker=response['Marker'])