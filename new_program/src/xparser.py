import operator


class Node(object):
    """表示语法树中的一个节点"""
    
    def eval(self):
        """子类应该实现的方法, 计算自身节点的方式"""
        # 不想写这句话用abc模块
        raise "需要子类实现"

    def repr(self):
        """子类应该实现的方法，用于数据展示"""
        raise "需要子类实现"
    
    def __str__(self):
        return self.repr()

    def __repr__(self):
        return self.repr()


class Interger(Node):
    """代表一个整数节点"""

    def __init__(self, token):
        self.token = token
    
    def eval(self):
        return int(self.token.value)

    def repr(self):
        return self.token.value


class OperatorExpression(Node):
    """代表一个算数表达式, 比如1+2"""
    operator_map = {
        "+": operator.add,
        "-": operator.sub,
        "*": operator.mul,
        "/": operator.truediv
    }
    
    def __init__(self, token, left, right):
        self.token = token
        self.op = self.operator_map[self.token.value]
        self.left = left
        self.right = right

    def eval(self):
        # 注意这里的left, right也可以是一个OperatorExpression，所以会递归调用
        return self.op(self.left.eval(), self.right.eval())

    def repr(self):
        # 注意这里的left, right也可以是一个OperatorExpression，所以会递归调用
        return "(" + self.left.repr() + self.token.value + self.right.repr() + ")"


class Parser(object):
    # 定义每个操作符的优先级，默认+-小于*/
    operator_precedence_map = {
        "EOF": 0,
        "+": 1,
        "-": 1,
        "*": 2,
        "/": 2,
    }

    def __init__(self, precedences=None):
        if precedences:
            self.operator_precedence_map.update(precedences)
    
    def parse_infix_expression(self, token, left):
        """
        解析中序表达式
        
        中序表达式是指操作符在两个对象之间, 比如+-*/, 有中序自然还有前序及后续，但是这里不涉及
        """
        precedence = self.operator_precedence_map[token.value]
        # 这里会递归调用parse_expression,但是传入的precedence最2，所以不会进入while循环
        right = self.parse_expression(precedence)
        expr = OperatorExpression(token, left, right)

        return expr

    def parse_integer(self, token):
        return Interger(token)

    def parse_expression(self, precedence=0):
        current_token = self.next_token
        self.next_token = self.next()
        left_expr = self.parse_integer(current_token)

        # 默认的precedence是0，所以当下一个token是+-*/的时候都会进入while循环，将表达式进行左结合，不断的递归
        # 而最后到EOF的时候，EOF的优先级是0, 所以导致while循环终止，返回最终的表达式
        while precedence < self.operator_precedence_map[self.next_token.value]:
            current_token = self.next_token
            self.next_token = self.next()

            left_expr = self.parse_infix_expression(current_token, left_expr)
        return left_expr

    def next(self):
        return next(self.iter_tokens)

    def parse(self, tokens):
        self.tokens = tokens
        self.iter_tokens = iter(tokens)
        self.next_token = self.next()
        return self.parse_expression()

    def eval(self, expression):
        return expression.eval()


if __name__ == "__main__":
    from xlexer import Lexer
    text = "1 + 2 - 3 * 4 / 5"
    mylexer = Lexer()
    myparser = Parser()
    tokens = mylexer.parse(text)
    expr = myparser.parse(tokens)
    print(expr)
    print(myparser.eval(expr))




