def lambda_handler(event, context):
    message = 'message: {}'.format(event['message'])
    return {
        'message': message
    }