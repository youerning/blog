custom_precedences = {
        "+": 2,
        "-": 2,
        "*": 1,
        "/": 1,
    }

if __name__ == "__main__":
    from xlexer import Lexer
    from xparser import Parser

    text = "1 + 2 - 3 * 4 / 5"
    mylexer = Lexer()
    myparser = Parser(custom_precedences)
    tokens = mylexer.parse(text)
    expr = myparser.parse(tokens)
    print(expr)
    print(myparser.eval(expr))
