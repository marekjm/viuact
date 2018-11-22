class Emitter_exception(Exception):
    pass

class Source_cannot_be_void(Emitter_exception):
    pass

class Lowerer_exception(Exception):
    pass

class No_such_function(Lowerer_exception):
    pass
