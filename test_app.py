# simple test app to test deephaven component
# run with: streamlit run test_app.py

import streamlit as st
from streamlit_deephaven import start_server, display_dh

start_server(jvm_args=["-DAuthHandlers=io.deephaven.auth.AnonymousAuthenticationHandler"])

st.subheader("Deephaven Component Demo")

# Create a deephaven component with a simple table
# Create a table and display it
from deephaven import time_table
from deephaven.plot.figure import Figure

t = time_table("PT1S").update(["x=i", "y=Math.sin(x)", "z=Math.cos(x)"])
display_dh(t, height=200)

f = Figure().plot_xy(series_name="Sine", t=t, x="x", y="y").show()
f = f.plot_xy(series_name="Cosine", t=t, x="x", y="z").show()
display_dh(f, height=400)

# Create a deephaven table that can be updated
seconds = st.selectbox("Seconds", [1, 2, 3], index=1)

t = time_table(f"PT{seconds}S").update([f"x={seconds}"])
display_dh(t, height=200, object_id="t")