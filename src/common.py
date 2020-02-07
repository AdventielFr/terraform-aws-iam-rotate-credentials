#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import os
import logging
import boto3
import datetime

class RefreshCredentialRequest(object):
    def __init__(self, **kwargs):
        self.user_name = None
        self.force = False
        self.access_key_ids = []
        self.login_profile = False
        self.__dict__.update(kwargs)
        if not self.user_name:
            raise ValueError("user_name is required")

class Common(object):

    def __init__(self):
        self._logger = logger = logging.getLogger()
        self._logger.setLevel(logging.INFO)

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

    def is_known_email(self, ses_client, user_name, email):
        self.logger.info(f'Check AWS SES email status ("{email}") for user "{user_name}"')
        response = ses_client.get_identity_verification_attributes(Identities=[email])
        status = None
        if email in response['VerificationAttributes']:
            status = response['VerificationAttributes'][email][
                'VerificationStatus']
            if status == 'Success':
                self.logger.info(f'User {user_name} s validated by AWS SES ( AWS SES email = {email}, status = {status} ).')
                return True
        return False

    def is_known_domain(self, ses_client, user_name, domain):
        self.logger.info(f'Check AWS SES domain status ("{domain}") for user "{user_name}"')
        response = ses_client.get_identity_verification_attributes(Identities=[domain])
        if domain in response['VerificationAttributes']:
            status = response['VerificationAttributes'][domain][
                'VerificationStatus']
        if status == 'Success':
            self.logger.info(f'User {user_name} is validated by AWS SES ( AWS SES domain = {domain}, status = {status} ).')
            return True
        return False
    
    def is_valid_email(self, ses_client, user_name, email):
        match = re.match(r"^[a-zA-Z0-9_.+-]+@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)$", email)
        if not match:
            message = f'For user {user_name}, {email} is not a valid email.'
            self.logger.warn(message)
            self.send_message(message,verbosity='WARN')
            return False
    
        # test user mail
        is_valid = self.is_known_email(ses_client, user_name, email)
        if is_valid:
            return True

        # test user domain
        domain = match.group(1)
        is_valid = self.is_known_domain(ses_client, user_name, domain)
        if is_valid:
            return True

        message = f'User {user_name} with email {email} is not validated by AWS SES.'
        self.logger.warn(message)
        self.send_message(message, verbosity='WARN')
        return False

    def to_int(self, value, default):
        try:
            return int(value)
        except:
            return default

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
