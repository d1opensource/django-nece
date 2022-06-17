class NonTranslatableFieldError(Exception):
    def __init__(self, fieldname):
        self.fieldname = fieldname
        message = f"{fieldname} is not in translatable fields"
        super(NonTranslatableFieldError, self).__init__(message)
