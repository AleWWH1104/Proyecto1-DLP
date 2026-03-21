class YALexError(Exception):
    # error en el proceso de generacion (parser, expansion, construccion)
    pass

class LexicalError(Exception):
    # error en el analizador lexico generado al procesar input
    def __init__(self, message: str, position: int = -1, context: str = ""):
        self.position = position
        self.context  = context
        super().__init__(message)

    def __str__(self):
        base = super().__str__()
        if self.position >= 0:
            return f"{base} (posicion {self.position})"
        return base

class CircularReferenceError(YALexError):
    # dependencia circular en definiciones 'let'
    pass
