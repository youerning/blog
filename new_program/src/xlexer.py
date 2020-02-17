# -*- coding: utf-8 -*-
from __future__ import print_function
import string
from collections import namedtuple

# 定义一个namedtuple类型的Token类型用于表示Token
Token = namedtuple("Token", ["type", "value"])


class Lexer(object):
    # 所有整型数字
    numbers = set(map(str, range(10)))
    # {'2', '9', '1', '0', '6', '3', '7', '5', '8', '4'}
    
    # 所有大小写英文字母
    letters = set(string.ascii_letters)
    # {'W', 'b', 'g', 'a', 'V', 'G', 'h', 'I', 'N', 'X', 'S', 'r', 'e', 'M', 'p', 'F', 'O', 'Z', 't', 'j', 'q', 'L', 'd', 'J', 'R', 'k', 'Y', 'D', 's', 'K', 'o', 'x', 'u', 'A', 'H', 'T', 'i', 'w', 'm', 'n', 'v', 'f', 'C', 'y', 'c', 'E', 'Q', 'P', 'l', 'B', 'z', 'U'}
    
    # 加减乘除
    ADD = "+"
    SUB = "-"
    MUL = "*"
    DIV = "/"
    operators = set([ADD, SUB, MUL, DIV])
    
    # END OF FILE 表示文本终结的Token
    EOF = Token("EOF", "EOF")

    def parse(self, text):
        self.tokens = []
        self.text = text
        self.cur_pos = 0
        self.cur_char = self.text[self.cur_pos]

        while self.cur_char is not self.EOF:
            if self.cur_char == " ":
                self.next()
                continue
            elif self.cur_char in self.numbers:
                token = self.read_integer()
            elif self.cur_char in self.operators:
                token = Token("operator", self.cur_char)
                self.next()
            else:
                raise "未知字符: %s" % self.cur_char

            self.tokens.append(token)
        
        # 加一个EOF是为了标识整段代码已经到尽头
        self.tokens.append(self.EOF)
        return self.tokens

    def next(self):
        """使当前字符的位置不断的向右移动"""
        self.cur_pos += 1
        if self.cur_pos >= len(self.text):
            self.cur_char = self.EOF
        else:
            self.cur_char = self.text[self.cur_pos]
    
    def read_integer(self):
        integer = self.cur_char
        self.next()
        while self.cur_char in self.numbers:
            integer += self.cur_char
            self.next()

        return Token("Integer", integer)


if __name__ == "__main__":
    text = "1 + 2"
    mylexer = Lexer()
    print("1+2")
    print(mylexer.parse("1+2"))
    print()
    print("3  *4/ 5")
    print(mylexer.parse("3  *4/ 5"))
