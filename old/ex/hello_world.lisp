; A function definition in Viuact begins with the "let" keyword. Then comes the
; name of the function, a list of its formal parameters (may be empty) and the
; expression that implements the function's body.
;
; A function's body is a single expression; it may be a compound expression but
; it still is a single expression. This yields a very elegant definition of a
; function in Viuact:
;
;       In Viuact, a function is a parametrised expression.
;
; The syntax rule for a function definition is incredibly simple:
;
;       "(" "let" name formal_parameters_list expression ")"
;
(let main () {
    ; A variable definition in Viuact is introduced by the "let" keyword (same
    ; as for a function definition). Then comes the name of the variable and
    ; a single expression that evaluates to the value of the variable.
    ;
    ; Let bindings (as this construction is called) are the only method of
    ; creating variables in Viuact.
    ;
    ; The abstract syntax for a variable definition is simple:
    ;
    ;       "(" "let" name expression ")"
    ;
    ; It is almost the same as the syntax for a function definition, lacking
    ; only the list of formal parameters. This is because let bindings are not
    ; parametrised expressions - they simply names bound to a certain value.
    ;
    ; Names can be rebound to a new value simply by reusing them in a subsequent
    ; let expression.
    ;
    (let greeting "Hello World!")

    ; A function call is a simple list whose first element is a name of a
    ; function and rest of the elements are expressions to be evaluated and
    ; bound to formal parameters (i.e. they become the "actual parameters" of
    ; the function.
    (print greeting)

    ; In Viuact, the return value of a function is simply the value of the last
    ; expression used inside its body. Thus we return 0 from the main function
    ; simply by stating a literal 0 as the last expression of the main function.
    0
})
