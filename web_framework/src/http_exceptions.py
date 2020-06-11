class BadRequestException(Exception):
    code = 400

class InternalServerErrorException(Exception):
    code = 500