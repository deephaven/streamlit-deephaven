import __main__
import os
import streamlit.components.v1 as components
from uuid import uuid4
from typing import List, Optional
import base64
import streamlit as st
import threading

DH_STATE = "_deephaven"

lock = threading.RLock()


def _str_object_type(obj):
    """Returns the object type as a string value"""
    return f"{obj.__class__.__module__}.{obj.__class__.__name__}"

# cache this so it is only started once and streamlit waits for it to be ready before rerunning
@st.cache_resource
def _create_ctx():
    """Open the Deephaven execution context. Required before performing any operations on the server."""
    from deephaven_server import Server
    # We store the execution context as an attribute on the server instance
    print("Initializing Context...")

    from deephaven.execution_context import get_exec_ctx
    Server.instance.__deephaven_ctx = get_exec_ctx()
    return Server.instance.__deephaven_ctx

# cache this so it is only started once and streamlit waits for it to be ready before rerunning
@st.cache_resource
def _starting_server(host: Optional[str] = None, port: Optional[int] = None, jvm_args: Optional[List[str]] = None):
    """Initialize the Deephaven server. This will start the server if it is not already running."""
    from deephaven_server import Server
    print("Initializing Deephaven Server...")
    s = Server(host=host, port=port, jvm_args=jvm_args)
    s.start()
    print("Deephaven Server listening on port", s.port)

    __main__.__dict__['MAIN_AND_DH_DRIFTED'] = False  # see next 'with lock:' block below
    Server.instance.__globals = __main__.__dict__

    # context should be created here to ensure it's created by the same thread that started the server
    _create_ctx()

    return Server.instance

def _remove_widgets():
    """Remove all widgets from the main module globals"""
    from deephaven_server import Server
    for object_id in st.session_state[DH_STATE]['to_delete']:
        Server.instance.__globals.pop(object_id, None)
    st.session_state[DH_STATE]['to_delete'] = []


def start_server(host: Optional[str] = None, port: Optional[int] = None, jvm_args: Optional[List[str]] = None):
    """
    Initialize the Deephaven server. This will start the server if it is not already running.
    This function should be called on every rerun of the streamlit app to ensure old objects are cleaned up.

    Args:
        host: The host to start the server on. Defaults to None.
        port: The port to start the server on. Defaults to None.
        jvm_args: A list of JVM arguments to pass to the server. Defaults to None.
    """
    from deephaven_server import Server
    server = _starting_server(host, port, jvm_args)

    with lock:
        # https://github.com/kzk2000/deephaven-streamlit/blob/f2bc09fcd900c2332db84456d210edb94d7c8106/app/src/streamlit_deephaven.py
        # Possibly handles a very rare race condition upon reloading many open Streamlit tabs
        # when the Streamlit server re-starts. Ensures that the most recent __main__.__dict__ of the latest
        # Streamlit server session is always stored as attribute on the server instance as well.
        if __main__.__dict__.get('MAIN_AND_DH_DRIFTED', True):
            __main__.__dict__['MAIN_AND_DH_DRIFTED'] = False
            Server.instance.__globals = __main__.__dict__

    # must open context per session
    Server.instance.__deephaven_ctx.j_exec_ctx.open()

    if not hasattr(st.session_state, DH_STATE):
        st.session_state[DH_STATE] = {"to_delete": []}

    # clear the to_delete list
    # this should run on every rerun to ensure old objects are removed on the server
    _remove_widgets()
    return server

# Create a wrapper function for the component. This is an optional
# best practice - we could simply expose the component function returned by
# `declare_component` and call it done. The wrapper allows us to customize
# our component's API: we can pre-process its input args, post-process its
# output value, and add a docstring for users.
def display_dh(widget, height=600, width=None, object_id=None, key=None, session=None):
    """Display a Deephaven widget.

    Parameters
    ----------
    widget: deephaven.table.Table | deephaven.plot.figure.Figure | pandas.core.frame.DataFrame | str
        The Deephaven widget we want to display. If a string is passed, a session must be specified.
    height: int
        The height of the widget in pixels
    width: int
        The width of the widget in pixels
    object_id: string
        The variable name of the Deephaven widget we want to display.
    key: str or None
        An optional key that uniquely identifies this component. If this is
        None, and the component's arguments are changed, the component will
        be re-mounted in the Streamlit frontend and lose its current state.
    session: pydeephaven.Session
        The session to use when displaying a remote Deephaven widget by name.
        Must be specified if a string is passed as the widget parameter.

    Returns
    -------
    string
        The object_id of the created object

    """
    from deephaven_server import Server

    # Call through to our private component function. Arguments we pass here
    # will be sent to the frontend, where they'll be available in an "args"
    # dictionary.
    #
    # "default" is a special argument that specifies the initial return
    # value of the component before the user has interacted with it.

    # Generate a nonce for the widget to ensure the iframe is reloaded
    # This is necessary in cases where widget or object_id is a string
    nonce = str(uuid4())

    if isinstance(widget, str):
        # a string widget must match the object_id
        object_id = widget
    elif object_id is None:
        # Generate a new table ID using a UUID prepended with a `__w_` prefix if name not specified
        object_id = f"__w_{str(uuid4()).replace('-', '_')}"

    if not isinstance(widget, str):
        # Set this object to be removed on rerun but only if the widget is not a remote object
        st.session_state[DH_STATE]['to_delete'].append(object_id)

    params = {"name": object_id, "nonce": nonce}

    if isinstance(widget, str):
        if session is None:
            raise ValueError(
                "session must be specified when using a remote pydeephaven object by name"
            )
        port = session.port
        server_url = f"http://{session.host}:{port}/"
    elif _str_object_type(widget) == "pydeephaven.table.Table":
        session = widget.session

        if b"envoy-prefix" in session._extra_headers:
            params["envoyPrefix"] = session._extra_headers[b"envoy-prefix"].decode(
                "ascii"
            )

        port = widget.session.port
        server_url = f"http://{widget.session.host}:{port}/"

        if hasattr(session, "session_manager"):
            params["authProvider"] = "parent"
            # We have a DnD session, and we can get the authentication and connection details from the session manager
            token = base64.b64encode(
                session.session_manager.auth_client.get_token(
                    "RemoteQueryProcessor"
                ).SerializeToString()
            ).decode("us-ascii")
            server_url = (
                widget.session.pqinfo().state.connectionDetails.staticUrl
            )

        session.bind_table(object_id, widget)
    else:
        port = Server.instance.port
        server_url = f"http://localhost:{port}/"

        # Add the table to the main modules globals list so it can be retrieved by the iframe
        Server.instance.__globals[object_id] = widget

    if "DEEPHAVEN_ST_URL" in os.environ:
        server_url = os.environ["DEEPHAVEN_ST_URL"]

    param_values = [f"{k}={v}" for k, v in params.items()]
    param_string = "?" + "&".join(param_values)

    if not server_url.endswith("/"):
        server_url = f"{server_url}/"

    # Generate the iframe_url from the object type
    iframe_url = f"{server_url}iframe/widget/{param_string}"

    # We don't really need the component value in the Deephaven example, since we're just creating a display widget...
    # Maybe if we were making a one click widget, that would make sense...
    # component_value = _component_func(iframe_url=iframe_url, object_type=object_type, width=width, height=height, key=key, default=0)
    return components.iframe(iframe_url, height=height, width=width)
