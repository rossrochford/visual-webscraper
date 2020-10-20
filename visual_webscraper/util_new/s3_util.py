import json
import os
import uuid

import boto3

S3_HOST = os.environ.get('S3_HOST', '127.0.0.1')
S3_PORT = int(os.environ.get('S3_PORT', 5001))


def _s3_data_upload(bucket, get_data_func, mime_type, ext):

    endpoint_url = 'http://%s:%s' % (S3_HOST, S3_PORT)

    sess = boto3.session.Session()
    client = sess.client(
        's3', endpoint_url=endpoint_url,
        # config=boto3.session.Config(signature_version='s3v4')
    )
    key = uuid.uuid4().hex + '.' + ext
    data_bytes = get_data_func()

    # with open(filepath, mode='rb') as file:  # b is important -> binary
        #file_bytes = file.read()

    client.put_object(
        Key=key, Bucket=bucket, ACL='public-read',
        Body=data_bytes, ContentType=mime_type
    )
    url = endpoint_url + '/' + bucket + '/' + key
    return key, url


def s3_json_upload(bucket, json_data):

    def get_data():
        js_data = json_data
        if type(js_data) is dict:
            js_data = json.dumps(json_data)
        return js_data.encode('utf-8')

    return _s3_data_upload(
        bucket, get_data, 'application/json', 'json'
    )


def s3_file_upload(bucket, filepath, mime_type, ext):

    def get_data():
        with open(filepath, mode='rb') as file:
            return file.read()

    return _s3_data_upload(
        bucket, get_data, mime_type, ext
    )
