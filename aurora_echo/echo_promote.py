##
# The MIT License (MIT)
#
# Copyright (c) 2016 BlackLocus
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
##

import json
import sys

import boto3
import click

from aurora_echo.echo_const import ECHO_MODIFY_STAGE, ECHO_PROMOTE_COMMAND, ECHO_PROMOTE_STAGE, ECHO_RETIRE_STAGE
from aurora_echo.echo_util import EchoUtil, log_prefix_factory, validate_input_param
from aurora_echo.entry import root

rds = boto3.client('rds')
route53 = boto3.client('route53')

log_prefix = log_prefix_factory(ECHO_PROMOTE_COMMAND)


def find_record_set(hosted_zone_id: str, record_set_name: str):

    paginator = route53.get_paginator('list_resource_record_sets')
    response_iterator = paginator.paginate(HostedZoneId=hosted_zone_id)

    for response in response_iterator:
        for record_set in response['ResourceRecordSets']:
            if record_set['Name'] == record_set_name:
                return record_set


def update_dns(hosted_zone_ids: tuple, record_set_name: str, cluster_endpoint: str, ttl: str, interactive: bool):
    for hosted_zone in hosted_zone_ids:
        record_set = find_record_set(hosted_zone, record_set_name)

        if record_set and record_set.get('ResourceRecords'):
            click.echo('{} Found record set {} currently pointed at {}'
                       .format(log_prefix(), record_set['Name'], record_set['ResourceRecords'][0]['Value']))
        else:
            click.echo('{} Inserting new record set {} in hosted zone {}'.format(log_prefix(), record_set_name, hosted_zone))

        params = {
            'HostedZoneId': hosted_zone,
            'ChangeBatch': {
                'Comment': 'Modified by Aurora Echo',
                'Changes': [
                    {
                        'Action': 'UPSERT',
                        'ResourceRecordSet': {
                            'Name': record_set_name,
                            'Type': 'CNAME',
                            'TTL': ttl,
                            'ResourceRecords': [
                                {
                                    'Value': cluster_endpoint
                                },
                            ],
                        }
                    },
                ]
            }
        }

        click.echo('{} Parameters:'.format(log_prefix()))
        click.echo(json.dumps(params, indent=4, sort_keys=True))

        if interactive:
            click.confirm('{} Ready to update DNS record with these settings?'.format(log_prefix()), abort=True)  # exits entirely if no

        # update to the found instance endpoint
        route53.change_resource_record_sets(**params)
        click.echo('{} Success! DNS updated in hosted zone {}'.format(log_prefix(), hosted_zone))


@root.command()
@click.option('--aws-account-number', '-a', callback=validate_input_param, required=True)
@click.option('--region', '-r', callback=validate_input_param, required=True)
@click.option('--managed-name', '-n', callback=validate_input_param, required=True)
@click.option('--hosted-zone-id', '-z', callback=validate_input_param, multiple=True, required=True)
@click.option('--record-set', '-rs', callback=validate_input_param, required=True)
@click.option('--ttl', default=60)
@click.option('--interactive', '-i', default=True, type=bool)
def promote(aws_account_number: str, region: str, managed_name: str, hosted_zone_id: tuple, record_set: str, ttl: str,
            interactive: bool):
    click.echo('{} Starting aurora-echo for {}'.format(log_prefix(), managed_name))
    util = EchoUtil(region, aws_account_number)

    # click doesn't allow mismatches between option and parameter names, so just for clarity, this is a tuple
    hosted_zone_ids = hosted_zone_id

    found_instance = util.find_instance_in_stage(managed_name, ECHO_MODIFY_STAGE)
    if found_instance and found_instance['DBInstanceStatus'] == 'available':
        click.echo('{} Found promotable instance: {}'.format(log_prefix(), found_instance['DBInstanceIdentifier']))
        cluster_endpoint = found_instance['Endpoint']['Address']

        update_dns(hosted_zone_ids, record_set, cluster_endpoint, ttl, interactive)

        old_promoted_instance = util.find_instance_in_stage(managed_name, ECHO_PROMOTE_STAGE)
        if old_promoted_instance:
            click.echo('{} Retiring old instance: {}'.format(log_prefix(), old_promoted_instance['DBInstanceIdentifier']))
            util.add_stage_tag(managed_name, old_promoted_instance, ECHO_RETIRE_STAGE)

        click.echo('{} Updating tag for promoted instance: {}'.format(log_prefix(), found_instance['DBInstanceIdentifier']))
        util.add_stage_tag(managed_name, found_instance, ECHO_PROMOTE_STAGE)

        click.echo('{} Done!'.format(log_prefix()))
    else:
        click.echo('{} No instance found in stage {} with status \'available\'. Not proceeding.'.format(log_prefix(), ECHO_MODIFY_STAGE))
        sys.exit(1)
