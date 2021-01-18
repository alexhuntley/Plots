from lark import Lark, Transformer

latex_parser = Lark(r"""
list : element*
?blist : "{" list "}"
?element : atom  | binary | operator | supersub | frac | radical | abs | paren | sum

atom : LETTER | DIGIT | "."

binary : "\times" -> times
       | "+" -> plus
       | "-" -> minus
       | "=" -> equals

OPNAME : LETTER+
operator : "\operatorname{" OPNAME "}"

supersub : ("_" blist) | ("^" blist) | ("_" blist "^" blist)

frac : "\frac" blist blist

radical : "\sqrt" ["[" list "]"] blist

abs.2 : "|" list "|"

LEFT : "(" | "[" | "\{"
RIGHT : ")" | "]" | "\}"
paren : LEFT -> left
      | RIGHT -> right

sum : "\sum" "_" blist "^" blist

%import common.LETTER
%import common.DIGIT

%import common.WS
%ignore WS
""", start='list')

class LatexTransformer(Transformer):
    pass
