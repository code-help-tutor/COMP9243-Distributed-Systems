WeChat: cstutorcs
QQ: 749389476
Email: tutorcs@163.com
#!/usr/bin/python3
import sys
import os
from commonlib import *

def main():
    if len(sys.argv) != 4:
        raise ValueError("Wrong paramater format!\nIt should be:\n./minimoto_setup keyfile aws_access_key_id aws_secret_access_key")
    keyfile = sys.argv[1]
    aws_access_key_id = sys.argv[2]
    aws_secret_access_key = sys.argv[3]
    """save to config file"""
    add_config(
        {
            CONFIG_KEYFILE_NAME: os.path.splitext(os.path.basename(keyfile))[0],
            CONFIG_KEYID: aws_access_key_id,
            CONFIG_KEY: aws_secret_access_key
        })
    """copy keyfile to a specific path and chmod"""
    normalize_pem(keyfile)
    """create SQS"""
    sqs = boto3_resource('sqs')
    queue = sqs.create_queue(
        QueueName = NAME_SQS,
        Attributes = {
            'VisibilityTimeout': TIMEOUT_SQS_MSG
        })
    add_config(
        {
            CONFIG_SQS_URL: queue.url
        }
    )
    """create S3 buckets"""
    s3 = boto3_resource('s3')
    bucket_input = s3.create_bucket(
        Bucket = NAME_BUCKET_INPUT,
        CreateBucketConfiguration = {
            'LocationConstraint': REGION
        })
    bucket_output = s3.create_bucket(
        Bucket = NAME_BUCKET_OUTPUT,
        CreateBucketConfiguration = {
            'LocationConstraint': REGION
        })
    """create EC2 security_group"""
    ec2 = boto3_resource('ec2')
    security_group = ec2.create_security_group(
        Description = NAME_SECURITY_GROUP,
        GroupName = NAME_SECURITY_GROUP
    )
    # setup ssh access
    security_group.authorize_ingress(
        CidrIp = '0.0.0.0/0',
        FromPort = 22,
        IpProtocol = "tcp",
        ToPort = 22
    )
    """create EC2 instances"""
    client = boto3_create_instance(ec2, DEFAULT_AMI, TYPE_CLIENT)
    setup_common_stuff(client)
    upload_config_file(client)
    upload_executable('minimoto_client', client)

    watchdog = boto3_create_instance(ec2, DEFAULT_AMI, TYPE_WATCHDOG)
    setup_common_stuff(watchdog)
    upload_executable('minimoto_watchdog', watchdog)
    scp_upload(keyfile, watchdog)
    ssh_do_cmd(watchdog, CMD_CHMOD.format(mode = 400, file = get_normalized_pem()))

    origin_transcode_service = boto3_create_instance(ec2, DEFAULT_AMI, TYPE_TRANSCODE_SERVICE)
    setup_common_stuff(origin_transcode_service)
    ssh_do_cmd(origin_transcode_service, CMD_INSTALL_TRANSCODE_SUPPORT)
    upload_config_file(origin_transcode_service)
    upload_executable('minimoto_transcode', origin_transcode_service)
    upload_executable('minimoto_transcode.sh', origin_transcode_service)
    scp_upload('transcode.cron', origin_transcode_service)

    """create transcode service image"""
    transcode_service_image = origin_transcode_service.create_image(Name = TYPE_TRANSCODE_SERVICE)
    add_config(
        {
            CONFIG_TRANSCODE_SERVICE_AMI: transcode_service_image.image_id
        }
    )

    upload_config_file(watchdog)

    origin_transcode_service.wait_until_running()
    ssh_do_cmd(origin_transcode_service, CMD_CRON_TRANSCODE)

    """print all the mandatory out messages"""
    print("SQS_REQUEST_QUEUE={}".format(NAME_SQS))
    print("S3_BUCKET_INPUT=s3://{}".format(NAME_BUCKET_INPUT))
    print("S3_BUCKET_OUTPUT=s3://{}".format(NAME_BUCKET_OUTPUT))
    print("CLIENT_USER={}".format(ASW_EC2_USER))
    print("CLIENT_ADDR={}".format(client.public_dns_name))
    print("WATCHDOG_USER={}".format(ASW_EC2_USER))
    print("WATCHDOG_ADDR={}".format(watchdog.public_dns_name))
    print("SERVICE_USER={}".format(ASW_EC2_USER))
    print("SERVICE_AMI={}".format(DEFAULT_AMI))

def setup_common_stuff(host_instance):
    ssh_do_cmd(host_instance, CMD_INSTALL_PIP)
    ssh_do_cmd(host_instance, CMD_INSTALL_BOTO3)
    scp_upload('commonlib.py', host_instance)

def upload_executable(file, host_instance):
    scp_upload(file, host_instance)
    ssh_do_cmd(host_instance, CMD_CHMOD.format(mode = 500, file = file))

if __name__ == '__main__':
    main()
