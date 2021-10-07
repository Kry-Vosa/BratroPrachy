
schema = {
    'button.size': {'type': 'integer', 'required': True},
    'button.spacing': {'type': 'integer', 'required': True},
    'buttons': {
        'type': 'list',
        'required': True,
        'schema': {
            'type': 'dict',
            'required': True,
            'schema': {
                'value': {'type': 'number', 'required': True},
                'text': {'type': 'string'},
                'color': {'type': 'string', 'regex': '^#[0-9a-fA-F]{6}$', 'default': '#CCCCCC'}
                }
            }
        }
    }
