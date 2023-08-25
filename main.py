import argparse
import boto3
import json
from datetime import datetime

parser = argparse.ArgumentParser(
    prog = 'aws-expired-stack-finder',
    description = 'Finds AWS Cloudformation stacks sharing a common environment suffix or prefix that are considered expired',
    epilog = 'Text at the bottom of help')

parser.add_argument(
    '--positional',
    '-p',
    choices=['prefix', 'sufix'],
    default='prefix',
    help='Where in the stack name to search for the environment identifier. Defaults to prefix')
parser.add_argument(
    '-d',
    '--delimiter',
    choices=['_', '-'],
    default='-',
    help='Logical delimiter to use when deconstructing stack names, e.g "dev-file-upload-api", "dev_file_upload_api". Defaults to "-")')
parser.add_argument(
    '--expiry',
    type=int,
    default=2,
    help='Number of days since stack was last updated until a stack is considered expired. Defaults to 2 (days)')
parser.add_argument(
    '-e',
    '--exclude',
    nargs='*',
    help='Environment identifier to exclude from list of expired stacks. Use this to ignore long standing stacks e.g. master, dev, test')
parser.add_argument(
    '-r',
    '--region',
    default='eu-west-1',
    help='AWS Region to search for the stacks')
parser.add_argument(
    '--profile',
    nargs='*',
    help='aws profile to use for all aws calls (optional)')

args = parser.parse_args()

cloudformation_client = boto3.client('cloudformation')

def get_stack_list():
    token_key = 'NextToken'
    next_token = None
    stacks = []
    included_status = ['CREATE_FAILED', 'CREATE_COMPLETE', 'ROLLBACK_FAILED', 'ROLLBACK_COMPLETE', 'DELETE_FAILED', 'UPDATE_COMPLETE', 'UPDATE_FAILED', 'UPDATE_ROLLBACK_FAILED', 'UPDATE_ROLLBACK_COMPLETE', 'IMPORT_COMPLETE', 'IMPORT_ROLLBACK_FAILED', 'IMPORT_ROLLBACK_COMPLETE']

    resp = cloudformation_client.list_stacks(StackStatusFilter=included_status)
    stacks = stacks + resp['StackSummaries']

    if token_key in resp.keys():
        next_token = resp[token_key]

    while next_token is not None:
        resp = cloudformation_client.list_stacks(NextToken=next_token, StackStatusFilter=included_status)
        stacks = stacks + resp['StackSummaries']

        next_token = resp[token_key] if token_key in resp.keys() else None

    return stacks

def find_expired_stacks(stacks, expiry_in_days):
    expired_stacks = []
    for stack in stacks:
        print(stack)

        if 'LastUpdatedTime' in stack:
            last_update_time = stack['LastUpdatedTime']
            if abs((datetime.now().astimezone() - last_update_time).days) > expiry_in_days:
                expired_stacks.append(stack)
        elif 'CreationTime' in stack:
            creation_time = stack['CreationTime']

            if abs((datetime.now().astimezone() - creation_time).days) > expiry_in_days:
                expired_stacks.append(stack)
    return expired_stacks

def group_stacks_to_env(stacks, env_name_positional, env_name_delimiter, excluded_env_names):
    envs = []
    for stack in stacks:
        stack_name_parts = stack['StackName'].split(env_name_delimiter)

        if len(stack_name_parts) == 0:
            continue

        env_name = stack_name_parts[0] if env_name_positional == 'prefix' else stack_name_parts[-1]

        if env_name in excluded_env_names:
            continue

        if env_name not in envs:
            envs.append(env_name)

    return envs

if __name__ == '__main__':
    stacks = get_stack_list()
    expired_stacks = find_expired_stacks(stacks, args.expiry)

    print(json.dumps(expired_stacks, indent=4, sort_keys=True, default=str))

    envs = group_stacks_to_env(expired_stacks, args.positional, args.delimiter, args.exclude)

    print(json.dumps(envs, indent=4, sort_keys=True, default=str))
