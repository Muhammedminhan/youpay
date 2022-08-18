from decouple import config

# Set True if using aws s3 for static/media file storage
STORAGE_AWS = config('STORAGE_AWS', True)

print("AWS STORAGE ", STORAGE_AWS)
if STORAGE_AWS:
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY', '')
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME', '')

    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', '')
    # TODO - Uncomment below code and configure if AWS is configured

    # AWS_S3_ENDPOINT_URL = 'https://s3.{}.amazonaws.com'.format(
    #     AWS_S3_REGION_NAME)
    #
    # AWS_CLOUDFRONT_DOMAIN = config('AWS_CLOUDFRONT_DOMAIN')
    #
    # AWS_S3_CUSTOM_DOMAIN = AWS_CLOUDFRONT_DOMAIN
    #
    # AWS_S3_OBJECT_PARAMETERS = {
    #     'CacheControl': 'max-age=86400',
    # }
    # AWS_LOCATION = config('AWS_LOCATION', 'static')
    # STATIC_URL = 'https://%s/%s/' % (AWS_CLOUDFRONT_DOMAIN, AWS_LOCATION)
    # STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    # COMPRESS_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    # COMPRESS_URL = STATIC_URL
    # MEDIAFILES_LOCATION = 'media'
    # DEFAULT_FILE_STORAGE = 'core.storages.backends.aws_s3.MediaStorage'
    # MEDIA_URL = "https://%s/%s/" % (
    #     AWS_CLOUDFRONT_DOMAIN, MEDIAFILES_LOCATION)
    # COMPRESS_ENABLED = True
    # COMPRESS_OFFLINE = False
    # AWS_IS_GZIPPED = True
    # GZIP_CONTENT_TYPES = (
    #     'text/css',
    #     'application/javascript',
    #     'application/x-javascript',
    #     'text/javascript'
    # )
else:
    MEDIAFILES_LOCATION = 'media'
    MEDIA_URL = "/%s/" % (MEDIAFILES_LOCATION)
