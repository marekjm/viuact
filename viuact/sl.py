import viuact.errors
import viuact.lexemes
import viuact.forms


def data_of_token(tok):
    return {
        'position': tok.at(),
        'text': str(tok),
    }

def data_of_lexeme(tok, tags):
    return {
        'tag': tags[tok.t()],
        'value': data_of_token(tok.tok()),
    }

def data_of_form(form, tok_tags):
    if tok_tags is None:
        tok_tags = {}
        for i, each in enumerate(viuact.lexemes.Lexeme.patterns):
            tok_tags[each] = i

    if type(form) is viuact.forms.Fn:
        return {
            'tag': 'Fn',
            'value': {
                'name': data_of_lexeme(form.name(), tok_tags),
                'parameters': [
                    data_of_form(each, tok_tags)
                    for each
                    in form.parameters()
                ],
                'body': data_of_form(form.body(), tok_tags),
            },
        }
    if type(form) is viuact.forms.Compound_expr:
        return {
            'tag': 'Ce',
            'value': {
                'body': [
                    data_of_form(each, tok_tags)
                    for each
                    in form.body()
                ],
            },
        }
    if type(form) is viuact.forms.Fn_call:
        return {
            'tag': 'Fn_call',
            'value': {
                'to': data_of_form(form.to(), tok_tags),
            },
        }
    if type(form) is viuact.forms.Name_ref:
        return {
            'tag': 'Nr',
            'value': {
                'name': data_of_lexeme(form.name(), tok_tags),
            },
        }
    if type(form) is viuact.forms.Primitive_literal:
        return {
            'tag': 'P',
            'value': {
                'value': data_of_lexeme(form.value(), tok_tags),
            },
        }
    return None
    # raise viuact.errors.Fail((0, 0,), 'cannot store form: {}'.format(
    #     form.__class__.__name__))
