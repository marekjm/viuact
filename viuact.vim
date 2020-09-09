" Vim syntax file
" Language:	Viuact
" Maintainer:	Marek Marecki <marekjm@ozro.pw>
" Last Change:	2020 May 09

"
" For help and more information see the following topics (:help <topic>):
"
" - syn-keyword
" - syn-match
" - syn-region
" - syn-priority
" - group-name
"
" Also, see the following web page, it may be helpful:
" https://learnvimscriptthehardway.stevelosh.com/chapters/45.html
"

" Quit when a syntax file was already loaded.
if exists("b:current_syntax")
    finish
endif

syntax keyword viuactTodo           contained FIXME TODO XXX
syntax match viuactComment          "\v\s*\zs;.*$" contains=viuactTodo
syntax region viuactBlockComment    start=/\v\(\*/ end=/\v\*\)/
    \ contains=viuactBlockComment,viuactTodo

syntax match viuactOperator         "\v\+"
syntax match viuactOperator         "\v-"
syntax match viuactOperator         "\v\*"
syntax match viuactOperator         "\v/"
syntax match viuactOperator         "\v\<"
syntax match viuactOperator         "\v\<\="
syntax match viuactOperator         "\v\>"
syntax match viuactOperator         "\v\>\="
syntax match viuactOperator         "\v\>"
syntax match viuactOperator         "\v\>\="
syntax match viuactOperator         "\v\="
syntax match viuactOperator         "\v-\>"
syntax match viuactOperator         "\v\<-"
syntax match viuactOperator         "\v!"
syntax match viuactOperator         "\v!\="
syntax match viuactOperator         "\v:\="
syntax match viuactOperator         "\v\^"
syntax match viuactOperator         "\v\&"
syntax match viuactOperator         "\v\|"
syntax match viuactOperator         "\v\|\>"
syntax match viuactOperator         "\v\~"
syntax match viuactOperator         "\v\$"
syntax match viuactOperator         "\v\@"
syntax match viuactOperator         "\v\%"
syntax match viuactOperator         "\v\?"
syntax match viuactOperator         "\v,"
syntax match viuactOperator         "\v\."
syntax match viuactOperator         "\v::"
syntax keyword viuactOperator       and not or

syntax match viuactFloat            "\<\(0\|[1-9][0-9]*\)\.[0-9][0-9]*\>"
syntax match viuactFloat            "-\(0\|[1-9][0-9]*\)\.[0-9][0-9]*\>"
syntax match viuactDecInt           "\<[1-9][0-9]*\>"
syntax match viuactDecInt           "-[1-9][0-9]*\>"
syntax match viuactDecInt           "\<0\>"
syntax match viuactHexInt           "\<0x[0-9a-f][0-9a-f]*\>"
syntax match viuactHexInt           "-0x[0-9a-f][0-9a-f]*\>"

syn match viuactSpecialChar         display contained
    \ "\\\(x\x\+\|\o\{1,3}\|.\|$\)"
syn match viuactSpecialChar         display contained "\\\(u\x\{4}\|U\x\{8}\)"
syntax region viuactString          start=/\vr?"/ skip=/\\\\\|\\"/ end=/\v"/
    \ contains=viuactSpecialChar

syntax match viuactModuleName       contained
    \ "\v[A-Z][A-Za-z0-9_]*(\.[A-Z][A-Za-z0-9_]*)*"
syntax match viuactEnumName         contained "\<[a-z][a-zA-Z0-9_]*"
syntax match viuactModuleOrCtor     "\v[A-Z][A-Za-z0-9_]*"
syntax match viuactIdentifier       contained "\<[a-z][a-zA-Z0-9_]*'*"

syntax keyword viuactConstant       infinity
syntax keyword viuactBoolean        true false

syntax keyword viuactFunction       print

syntax keyword viuactStatement      module skipwhite nextgroup=viuactModuleName
syntax keyword viuactStatement      import skipwhite nextgroup=viuactModuleName
syntax keyword viuactStatement      let val skipwhite nextgroup=viuactIdentifier

syntax keyword viuactConditional    if match
syntax keyword viuactConditional    with skipwhite nextgroup=viuactModuleName

syntax keyword viuactLabel          default

syntax keyword viuactKeyword        of in do return

syntax keyword viuactException      try
syntax keyword viuactException      catch throw skipwhite nextgroup=viuactModuleName

syntax keyword viuactSpecial        actor defer tailcall watchdog

syntax keyword viuactType           i8 i16 i32 i64 f32 f64 bool bits string
syntax keyword viuactStorageClass   static
syntax keyword viuactStructure      enum skipwhite nextgroup=viuactEnumName
syntax keyword viuactStructure      struct vector exception

syntax match viuactCompoundExpr     "[{}]"

syntax keyword viuactDrop           _


highlight link viuactComment        Comment
highlight link viuactBlockComment   Comment
highlight link viuactTodo           Todo

highlight link viuactOperator       Operator

highlight link viuactString         String
highlight link viuactDecInt         Number
highlight link viuactHexInt         Number
highlight link viuactFloat          Float
highlight link viuactBoolean        Boolean
highlight link viuactConstant       Constant

highlight link viuactFunction       Function

highlight link viuactStatement      Statement
highlight link viuactConditional    Conditional
highlight link viuactIdentifier     Identifier
highlight link viuactModuleName     Label
highlight link viuactLabel          Label
highlight link viuactEnumName       Label
highlight link viuactKeyword        Keyword
highlight link viuactException      Exception
highlight link viuactSpecial        Special
highlight link viuactModuleOrCtor   Special

highlight link viuactType           Type
highlight link viuactStorageClass   StorageClass
highlight link viuactStructure      Structure

highlight link viuactCompoundExpr   Special
highlight link viuactDrop           SpecialChar
highlight link viuactSpecialChar    SpecialChar

let b:current_syntax = "viuact"
