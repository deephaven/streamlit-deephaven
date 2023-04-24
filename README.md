# Deephaven Streamlit Component

This component displays Deephaven widgets within Streamlit.

## Quickstart

1. In a new folder, set up your [Streamlit environment](https://docs.streamlit.io/library/get-started/installation) and install the `streamlit-deephaven` package:

```
python -m venv .venv
source .venv/bin/activate
pip install streamlit-deephaven
```

2. Create your first deephaven application, named `deephaven_app.py`:

```
import streamlit as st
from streamlit_deephaven import start_server, display_dh

# Start the Deephaven server. You must start the server before running any Deephaven operations.
start_server()

st.subheader("Streamlit Deephaven")

# Create a simple table.
from deephaven import empty_table
t = empty_table(1000).update(["x=i", "y=x * x"])

# Display the table.
display_dh(t)
```

3. Run the streamlit application:

```
streamlit run deephaven_app.py
```

## Alternate Deephaven Server URL
By default, the Deephaven server is located at `http://localhost:{port}`, where `{port}` is the port set in the Deephaven server creation call. If the server is not there, such as when running Streamlit in a Docker container, modify the `DEEPHAVEN_ST_URL` environmental variable to the correct URL before calling `display_dh`. 
```python
import os
os.environ["DEEPHAVEN_ST_URL"] = "http://localhost:1234"
```

For more information on running Streamlit, see the [Streamlit documentation](https://docs.streamlit.io/).

## Development

See [development guide](./development.md) for instructions on how to develop this package.
