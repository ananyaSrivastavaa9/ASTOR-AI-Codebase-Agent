QUESTIONS = [
    {
        "q": "Where is routing handled in Flask?",
        "expected_file": "scaffold.py",
        "expected_function": "add_url_rule",
    },
    {
        "q": "Where does Flask create the application object?",
        "expected_file": "app.py",
        "expected_function": "Flask",
    },
    {
        "q": "How are blueprints registered?",
        "expected_file": "blueprints.py",
        "expected_function": "register",
    },
    {
        "q": "Where is request context handled?",
        "expected_file": "ctx.py",
        "expected_function": "RequestContext",
    },
    {
        "q": "Where are Flask sessions opened?",
        "expected_file": "sessions.py",
        "expected_function": "open_session",
    },
    {
        "q": "Where does Flask handle exceptions?",
        "expected_file": "app.py",
        "expected_function": "handle_exception",
    },
    {
        "q": "Where is JSON response handling implemented?",
        "expected_file": "json/provider.py",
        "expected_function": "dumps",
    },
    {
        "q": "Where is Flask configuration stored?",
        "expected_file": "config.py",
        "expected_function": "Config",
    },
    {
        "q": "Where are command line commands handled?",
        "expected_file": "cli.py",
        "expected_function": "main",
    },
    {
        "q": "Where is url_for implemented?",
        "expected_file": "helpers.py",
        "expected_function": "url_for",
    },
    {
        "q": "Where are templates rendered?",
        "expected_file": "templating.py",
        "expected_function": "render_template",
    },
    {
        "q": "Where are signals defined?",
        "expected_file": "signals.py",
        "expected_function": "Namespace",
    },
    {
        "q": "Where is Flask logging configured?",
        "expected_file": "logging.py",
        "expected_function": "create_logger",
    },
    {
        "q": "Where are HTTP wrappers defined?",
        "expected_file": "wrappers.py",
        "expected_function": "Request",
    },
    {
        "q": "Where is send_file implemented?",
        "expected_file": "helpers.py",
        "expected_function": "send_file",
    },
    {
        "q": "Where are testing utilities implemented?",
        "expected_file": "testing.py",
        "expected_function": "FlaskClient",
    },
    {
        "q": "Where is application dispatch handled?",
        "expected_file": "app.py",
        "expected_function": "dispatch_request",
    },
    {
        "q": "Where are URL rules added?",
        "expected_file": "sansio/scaffold.py",
        "expected_function": "add_url_rule",
    },
    {
        "q": "Where is abort implemented?",
        "expected_file": "helpers.py",
        "expected_function": "abort",
    },
    {
        "q": "Where are Flask globals managed?",
        "expected_file": "globals.py",
        "expected_function": "request",
    },
]