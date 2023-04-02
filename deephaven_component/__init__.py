import __main__
import os
import streamlit.components.v1 as components
from uuid import uuid4

# Create a _RELEASE constant. We'll set this to False while we're developing
# the component, and True when we're ready to package and distribute it.
# (This is, of course, optional - there are innumerable ways to manage your
# release process.)
_RELEASE = False

# Declare a Streamlit component. `declare_component` returns a function
# that is used to create instances of the component. We're naming this
# function "_component_func", with an underscore prefix, because we don't want
# to expose it directly to users. Instead, we will create a custom wrapper
# function, below, that will serve as our component's public API.

# It's worth noting that this call to `declare_component` is the
# *only thing* you need to do to create the binding between Streamlit and
# your component frontend. Everything else we do in this file is simply a
# best practice.

if not _RELEASE:
    _component_func = components.declare_component(
        # We give the component a simple, descriptive name ("deephaven_component"
        # does not fit this bill, so please choose something better for your
        # own component :)
        "deephaven_component",
        # Pass `url` here to tell Streamlit that the component will be served
        # by the local dev server that you run via `npm run start`.
        # (This is useful while your component is in development.)
        url="http://localhost:3001",
    )
else:
    # When we're distributing a production version of the component, we'll
    # replace the `url` param with `path`, and point it to to the component's
    # build directory:
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    build_dir = os.path.join(parent_dir, "frontend/build")
    _component_func = components.declare_component("deephaven_component", path=build_dir)

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
def deephaven_component(deephaven_object, key=None):
    """Create a new instance of "deephaven_component".

    Parameters
    ----------
    table: deephaven.table.Table | deephaven.plot.figure.Figure | pandas.core.frame.DataFrame
        The Deephaven widget we want to display
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

    # Generate a new table ID using a UUID prepended with a `t_` prefix
    object_id = f"t_{str(uuid4()).replace('-', '_')}"

    print("Setting iframe_url...")
    # Generate the iframe_url from the object type
    server_url = f"http://localhost:{Server.instance.port}"
    iframe_url = f"{server_url}/iframe/{_path_for_object(deephaven_object)}/?name={object_id}"
    object_type = _str_object_type(deephaven_object)


    # Add the table to the main modules globals list so it can be retrieved by the iframe
    __main__.__dict__[object_id] = deephaven_object

    # We don't really need the component value in the Deephaven example, since we're just creating a display widget...
    # Maybe if we were making a one click widget, that would make sense...
    component_value = _component_func(iframe_url=iframe_url, object_type=object_type, key=key, default=0)

    return object_id


# Add some test code to play with the component while it's in development.
# During development, we can run this just as we would any other Streamlit
# app: `$ streamlit run deephaven_component/__init__.py`
if not _RELEASE:
    import streamlit as st
    
    print("Starting Deephaven Server...")
    # Start up the Deephaven Server
    from deephaven_server import Server
    s = Server(port=8899)
    s.start()
    print("Deephaven Server started!")

    st.subheader("Deephaven Component Demo")



    # Create a deephaven component with a simple table
    # Create a table and display it
    from deephaven import empty_table
    t = empty_table(1000).update("x=i")
    object_id = deephaven_component(t)
    st.markdown("Object_id is %s!" % str(object_id))
