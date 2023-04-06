import __main__
import os
import streamlit.components.v1 as components
from uuid import uuid4

DEV_MODE = os.environ.get("DH_DEV_MODE", False)

def _str_object_type(obj):
  """Returns the object type as a string value"""
  return f"{obj.__class__.__module__}.{obj.__class__.__name__}"

def _path_for_object(obj):
  """Return the iframe path for the specified object. Inspects the class name to determine."""
  name = _str_object_type(obj)

  if name in ('deephaven.table.Table', 'pandas.core.frame.DataFrame'):
    return 'table'
  if name == 'deephaven.plot.figure.Figure':
    return 'chart'
  raise TypeError(f"Unknown object type: {name}")

# Create a wrapper function for the component. This is an optional
# best practice - we could simply expose the component function returned by
# `declare_component` and call it done. The wrapper allows us to customize
# our component's API: we can pre-process its input args, post-process its
# output value, and add a docstring for users.
def display_dh(widget, height=600, width=None, object_id=None, key=None):
    """Display a Deephaven widget.

    Parameters
    ----------
    widget: deephaven.table.Table | deephaven.plot.figure.Figure | pandas.core.frame.DataFrame
        The Deephaven widget we want to display
    height: int
        The height of the widget in pixels
    width: int
        The width of the widget in pixels
    object_id: string
        The variable name of the Deephaven widget we want to display
    key: str or None
        An optional key that uniquely identifies this component. If this is
        None, and the component's arguments are changed, the component will
        be re-mounted in the Streamlit frontend and lose its current state.

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

    # Generate a new table ID using a UUID prepended with a `__w_` prefix if name not specified
    if object_id is None:
        object_id = f"__w_{str(uuid4()).replace('-', '_')}"

    # Generate the iframe_url from the object type
    server_url = f"http://localhost:{Server.instance.port}"
    iframe_url = f"{server_url}/iframe/{_path_for_object(widget)}/?name={object_id}"
    object_type = _str_object_type(widget)

    # Add the table to the main modules globals list so it can be retrieved by the iframe
    __main__.__dict__[object_id] = widget

    # We don't really need the component value in the Deephaven example, since we're just creating a display widget...
    # Maybe if we were making a one click widget, that would make sense...
    # component_value = _component_func(iframe_url=iframe_url, object_type=object_type, width=width, height=height, key=key, default=0)
    return components.iframe(iframe_url, height=height, width=width)


# Add some test code to play with the component while it's in development.
# During development, we can run this just as we would any other Streamlit
# app: `$ streamlit run streamlit_deephaven/__init__.py`
if DEV_MODE:
    import streamlit as st
    
    @st.cache_resource
    def init_server():
        print("Starting Deephaven Server...")
        # Start up the Deephaven Server
        from deephaven_server import Server
        s = Server(port=8899)
        s.start()
        print("Deephaven Server started!")
        return s
    s = init_server()

    @st.cache_resource
    def init_ctx():
        # Cache context initiation so that it is only created once
        from deephaven.execution_context import get_exec_ctx
        print("Getting Deephaven Context...")
        return get_exec_ctx()
    main_exec_ctx = init_ctx()

    st.subheader("Deephaven Component Demo")

    # Create a deephaven component with a simple table
    # Create a table and display it
    with main_exec_ctx:
      from deephaven import time_table
      from deephaven.plot.figure import Figure
      t = time_table("00:00:01").update(["x=i", "y=Math.sin(x)", "z=Math.cos(x)"])
      display_dh(t, height=200)

      f = Figure().plot_xy(series_name="Sine", t=t, x="x", y="y").show()
      f = f.plot_xy(series_name="Cosine", t=t, x="x", y="z").show()
      display_dh(f, height=400)
